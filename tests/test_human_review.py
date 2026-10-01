"""The human-review database: 160 completed reviews, and the rules that keep them usable.

The defect these tests exist for was found by looking rather than by reading.
`data/human_review/filled/` held 160 completed, signed, reasoned reviews. The loader read
only `data/human_review/queue_*.csv`, every one of which was unlabelled. So the human-review
feature was inert: 13 rows asserting the candidate *was* mentioned were discarded on every
run, the tests passed, and the docstring described a merge step that did not exist.

Nothing errored, which is why it survived. A silent discard of human labour looks exactly
like a model that has nothing to add.

So the properties are:

1. **A completed review is visible**, wherever the work has actually been done.
2. **A review cannot invent a category.** The schema's vocabularies are closed lists, and a
   typo in `lga` would otherwise create a risk band for a place that does not exist.
3. **`mentions` and `opposition` must be real booleans.** The old coercion was
   `str(value).lower() in ("true", "1", "yes")`, so a missing key or the string "yes"
   silently became `False` — which for `mentions` means a reviewed post that does reference
   the candidate is dropped from the counts with nothing logged.
4. **An unsigned or unreasoned row is not a review.** `data/human_review/README.md` requires
   all four signature fields and rejects vague reasoning; that was prose nobody could
   enforce.
5. **`unclear` is a label, not a place.** It is a legitimate reviewer verdict and its rows
   stay in the statewide figures, but no per-LGA output may present it as a location.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.aggregation import aggregate, reviews


GOOD_LABEL = {
    "sentiment": "neutral",
    "intensity": "moderate",
    "lga": "Bauchi",
    "mentions": True,
    "opposition": False,
    "language": "hausa",
}
GOOD_SIGNATURE = {
    "reviewer_label": "corrected",
    "reviewer_reasoning": (
        "Model read this as not about the candidate, but the post names Adamu "
        "explicitly and criticises the water record."),
    "reviewed_by": "test-reviewer",
    "reviewed_at": "2026-10-01",
}


def label(**overrides) -> dict:
    """A valid `final_label`, with named keys overridden or removed."""
    value = {**GOOD_LABEL, **overrides}
    for key, drop in list(value.items()):
        if drop is None:
            del value[key]
    return value


def row(raw_id="nairaland-abc123", final_label=None, signed=True, **overrides):
    """One queue row.

    `signed=False` is the realistic state of an untouched queue row: no verdict AND no
    signature. A row with a signature but no verdict is a different thing and is not
    something a fixture should create by accident.
    """
    body = {"raw_id": raw_id, "final_label": ""}
    if signed:
        body.update(GOOD_SIGNATURE)
    if final_label is not None:
        body["final_label"] = (final_label if isinstance(final_label, str)
                               else json.dumps(final_label))
    body.update(overrides)
    return body


def write_queue(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["raw_id", "final_label", "reviewer_label", "reviewer_reasoning",
              "reviewed_by", "reviewed_at"]
    import csv as _csv
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ReviewQueueTestCase(unittest.TestCase):
    """Point the review module at a temporary directory for every test.

    The restore is registered with addCleanup rather than done inline, because a test that
    raises mid-body would otherwise leave the module pointing at a deleted temp directory
    and every later test would read nothing -- which looks exactly like "the reviews are
    gone" rather than "a fixture leaked".
    """

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        real_dir = reviews.REVIEW_DIR
        reviews.REVIEW_DIR = self.directory
        self.addCleanup(setattr, reviews, "REVIEW_DIR", real_dir)

    def write(self, relative, rows):
        path = self.directory / relative
        write_queue(path, rows)
        return path


class TestReviewsAreVisible(ReviewQueueTestCase):
    def test_a_review_in_the_queue_is_loaded(self):
        self.write("queue_a.csv", [row(final_label=label())])
        found, problems = reviews.load_reviews()
        self.assertEqual(len(found), 1)
        self.assertEqual(problems, [])
        self.assertEqual(found["nairaland-abc123"]["sentiment"], "neutral")

    def test_a_review_in_filled_is_also_loaded(self):
        # THE regression. Reading only the queues made this row invisible.
        self.write("queue_a.csv", [row(signed=False)])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        found, problems = reviews.load_reviews()
        self.assertEqual(len(found), 1, f"completed work was discarded: {problems}")
        self.assertEqual(problems, [])

    def test_an_unfilled_queue_row_is_not_a_problem(self):
        # 730 rows are waiting for review. That is the normal state, not an error.
        self.write("queue_a.csv", [row(signed=False), row("nairaland-def456", signed=False)])
        found, problems = reviews.load_reviews()
        self.assertEqual(found, {})
        self.assertEqual(problems, [])

    def test_the_same_review_in_both_places_is_not_a_conflict(self):
        self.write("queue_a.csv", [row(final_label=label())])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        found, problems = reviews.load_reviews()
        self.assertEqual(len(found), 1)
        self.assertEqual(problems, [])

    def test_two_different_reviews_for_one_row_are_both_refused(self):
        # Which of two contradictory human judgements wins is a reviewer's decision. This
        # module guessing would put an unreviewed label into the counts.
        self.write("queue_a.csv", [row(final_label=label())])
        self.write("filled/queue_a.csv",
                   [row(final_label=label(sentiment="negative"))])
        found, problems = reviews.load_reviews()
        self.assertEqual(found, {})
        self.assertEqual([p.reason for p in problems],
                         ["conflicting_reviews_for_same_row"])

    def test_a_malformed_label_is_reported_not_swallowed(self):
        self.write("queue_a.csv", [row(final_label="not json at all")])
        found, problems = reviews.load_reviews()
        self.assertEqual(found, {})
        self.assertEqual([p.reason for p in problems], ["final_label_is_not_json"])


class TestVocabularyIsClosed(ReviewQueueTestCase):
    """A review may change what a post is. It may not invent a category."""

    def _reason(self, label):
        self.write("queue_a.csv", [row(final_label=label)])
        _found, problems = reviews.load_reviews()
        return problems[0].reason if problems else None

    def test_an_unknown_sentiment_is_refused(self):
        reason = self._reason({**GOOD_LABEL, "sentiment": "very-angry"})
        self.assertTrue(reason.startswith("sentiment_not_in_vocabulary"), reason)

    def test_an_unknown_lga_is_refused(self):
        # The one that mattered: a typo here creates a row in lga_daily.csv and a risk band
        # in risk.csv for a place that does not exist.
        reason = self._reason({**GOOD_LABEL, "lga": "Bauchii"})
        self.assertTrue(reason.startswith("lga_not_in_vocabulary"), reason)

    def test_an_unknown_language_is_refused(self):
        reason = self._reason({**GOOD_LABEL, "language": "pidgin"})
        self.assertTrue(reason.startswith("language_not_in_vocabulary"), reason)

    def test_an_unknown_intensity_is_refused(self):
        # Intensity is ordinal: the README says correct clear misses, do not fine-tune
        # levels. A level outside the rubric is not a level.
        reason = self._reason({**GOOD_LABEL, "intensity": "slightly-moderate"})
        self.assertTrue(reason.startswith("intensity_not_in_vocabulary"), reason)

    def test_unclear_is_a_valid_lga_verdict(self):
        # Not everything must name a place. Refusing `unclear` would push reviewers into
        # guessing an LGA, which is the failure the schema's `unclear` exists to prevent.
        self.write("queue_a.csv", [row(final_label=label(lga="unclear"))])
        found, problems = reviews.load_reviews()
        self.assertEqual(len(found), 1, problems)
        self.assertEqual(found["nairaland-abc123"]["lga"], "unclear")

    def test_a_missing_field_is_named_in_the_reason(self):
        partial = label(lga=None)
        reason = self._reason(partial)
        self.assertEqual(reason, "final_label_missing:lga")

    def test_an_unexpected_field_is_refused(self):
        reason = self._reason({**GOOD_LABEL, "sentiment_confidence": 1.0})
        self.assertTrue(reason.startswith("final_label_unexpected"), reason)

    def test_the_review_vocabularies_cover_everything_the_model_emits(self):
        # The schema is a TypeSafe rubric with prose criteria, not an option list, so
        # there is nothing machine-readable there to compare against. What does bite is
        # the classified data: if the model starts emitting a sentiment or an LGA the
        # review vocabulary does not know, a reviewer who correctly echoes that value
        # would have their work refused, and the refusal would be indistinguishable from
        # a typo. So the review vocabularies must cover the model's output.
        seen: dict[str, set[str]] = {"sentiment": set(), "lga": set(),
                                     "language": set(), "intensity": set()}
        columns = {"sentiment": "sentiment_label", "lga": "lga_relevance_label",
                   "language": "language_label", "intensity": "intensity_score"}
        import csv as _csv
        for path in sorted(Path("data/classified").glob("*.csv")):
            if path.name.startswith("pilot"):
                continue
            with path.open(encoding="utf-8", newline="") as handle:
                for row in _csv.DictReader(handle):
                    for key, column in columns.items():
                        seen[key].add((row.get(column) or "").strip())
        for key in seen:
            seen[key].discard("")
        self.assertEqual(seen["sentiment"] - set(reviews.SENTIMENT_LABELS), set(),
                         "the model emits a sentiment no review may state")
        self.assertEqual(seen["lga"] - set(reviews.REVIEWED_LGA_LABELS), set(),
                         "the model emits an LGA no review may state")
        self.assertEqual(seen["language"] - set(reviews.LANGUAGE_LABELS), set(),
                         "the model emits a language no review may state")
        self.assertEqual(seen["intensity"] - set(reviews.INTENSITY_LEVELS), set(),
                         "the model emits an intensity level no review may state")


class TestBooleansMustBeBooleans(ReviewQueueTestCase):
    """The worst failure available here: a true positive silently becoming a negative one."""

    def _reason(self, value):
        self.write("queue_a.csv", [row(final_label=label(mentions=value))])
        _found, problems = reviews.load_reviews()
        return problems[0].reason if problems else None

    def test_yes_is_not_a_boolean(self):
        # The old coercion accepted "yes". That is the coercion this replaces: a reviewer
        # asserting the candidate IS mentioned could be read as "not mentioned".
        self.assertEqual(self._reason("yes"), "mentions_must_be_a_json_boolean")

    def test_the_string_true_is_not_a_boolean(self):
        self.assertEqual(self._reason("True"), "mentions_must_be_a_json_boolean")

    def test_one_is_not_a_boolean(self):
        self.assertEqual(self._reason(1), "mentions_must_be_a_json_boolean")

    def test_a_missing_mentions_key_is_refused_not_defaulted(self):
        partial = label(mentions=None)
        self.write("queue_a.csv", [row(final_label=partial)])
        _found, problems = reviews.load_reviews()
        self.assertEqual([p.reason for p in problems], ["final_label_missing:mentions"])

    def test_opposition_is_held_to_the_same_rule(self):
        self.write("queue_a.csv", [row(final_label=label(opposition="no"))])
        _found, problems = reviews.load_reviews()
        self.assertEqual([p.reason for p in problems],
                         ["opposition_must_be_a_json_boolean"])

    def test_real_booleans_are_kept_as_booleans(self):
        for value in (True, False):
            with self.subTest(value=value):
                self.write("queue_a.csv", [row(final_label=label(mentions=value))])
                found, problems = reviews.load_reviews()
                self.assertEqual(problems, [])
                self.assertIs(found["nairaland-abc123"]["mentions"], value)


class TestTheSignatureIsRequired(ReviewQueueTestCase):
    """data/human_review/README.md required all four. It was prose. Now it is code."""

    def _reasons(self, **overrides):
        self.write("queue_a.csv", [row(final_label=label(), **overrides)])
        _found, problems = reviews.load_reviews()
        return sorted(p.reason for p in problems)

    def test_a_valid_review_is_accepted(self):
        self.assertEqual(self._reasons(), [])

    def test_an_unsigned_review_is_refused(self):
        self.assertEqual(self._reasons(reviewed_by=""), ["missing_signature:reviewed_by"])

    def test_an_undated_review_is_refused(self):
        self.assertEqual(self._reasons(reviewed_at=""), ["missing_signature:reviewed_at"])

    def test_an_unreasoned_override_is_refused(self):
        self.assertEqual(self._reasons(reviewer_reasoning=""),
                         ["missing_signature:reviewer_reasoning"])

    def test_a_review_with_no_model_comparison_is_refused(self):
        # reviewer_label is what tells the weekly eval a schema problem from a one-off.
        self.assertEqual(self._reasons(reviewer_label=""),
                         ["missing_signature:reviewer_label"])

    def test_vague_reasoning_is_refused(self):
        # "vague reasoning ('looks wrong') is rejected", per the README.
        self.assertEqual(self._reasons(reviewer_reasoning="looks wrong"),
                         [f"reasoning_too_short:{len('looks wrong')}"])

    def test_the_signature_is_checked_before_the_values(self):
        # An unsigned row is not evidence, whatever it says, so validating its vocabulary
        # first would produce a more confusing reason.
        self.write("queue_a.csv",
                   [row(final_label=label(sentiment="nonsense"), reviewed_by="")])
        _found, problems = reviews.load_reviews()
        self.assertEqual([p.reason for p in problems], ["missing_signature:reviewed_by"])


class TestUnclearIsNotAPlace(unittest.TestCase):
    def test_unclear_is_not_an_assigned_lga(self):
        self.assertFalse(reviews.is_assigned_lga("unclear"))

    def test_all_twenty_lgas_are_assigned(self):
        for lga in reviews.BAUCHI_LGAS:
            with self.subTest(lga=lga):
                self.assertTrue(reviews.is_assigned_lga(lga))
        self.assertEqual(len(reviews.BAUCHI_LGAS), 20)

    def test_a_nonsense_value_is_not_an_lga(self):
        for value in ("Bauchii", "", None, 42):
            with self.subTest(value=value):
                self.assertFalse(reviews.is_assigned_lga(value))


class TestApplyReviews(unittest.TestCase):
    """The reviewed row leaves the queue and joins the usable pool."""

    def _frame(self):
        return pd.DataFrame([{
            "raw_id": "nairaland-abc123",
            "routing_decision": "human_review",
            "sentiment_label": "not_about_candidate",
            "lga_relevance_label": "unclear",
            "language_label": "english",
            "intensity_score": "calm",
            "mentions_candidate_probability": 0.12,
            "opposition_signal_probability": 0.05,
            "sentiment_confidence": 0.41,
            "lga_confidence": 0.44,
        }])

    def _review(self, **over):
        return {**{k: v for k, v in GOOD_LABEL.items()}, "reviewer_label": "corrected",
                "reviewer_reasoning": GOOD_SIGNATURE["reviewer_reasoning"],
                "reviewed_by": "t", "reviewed_at": "2026-10-01", **over}

    def test_a_reviewed_row_becomes_human_cleared(self):
        df, cleared = aggregate.apply_reviews(
            self._frame(), {"nairaland-abc123": self._review()})
        self.assertEqual(cleared, 1)
        self.assertEqual(df.at[0, "routing_decision"], "human_cleared")

    def test_the_reviewers_label_replaces_the_models(self):
        df, _cleared = aggregate.apply_reviews(
            self._frame(), {"nairaland-abc123": self._review()})
        self.assertEqual(df.at[0, "sentiment_label"], "neutral")
        self.assertEqual(df.at[0, "lga_relevance_label"], "Bauchi")
        self.assertEqual(df.at[0, "language_label"], "hausa")
        self.assertEqual(df.at[0, "intensity_score"], "moderate")

    def test_mentions_true_becomes_a_relevant_probability(self):
        # The whole point. The model said 0.12; the reviewer says it does mention the
        # candidate, so the row has to clear the 0.5 relevance threshold.
        df, _cleared = aggregate.apply_reviews(
            self._frame(), {"nairaland-abc123": self._review(mentions=True)})
        self.assertEqual(df.at[0, "mentions_candidate_probability"], 1.0)
        relevant = ((df["mentions_candidate_probability"] >= 0.5)
                    & (df["sentiment_label"] != "not_about_candidate"))
        usable = relevant & df["routing_decision"].isin(["auto", "human_cleared"])
        self.assertTrue(bool(usable.iloc[0]))

    def test_confidence_is_pinned_to_one_because_a_person_stands_behind_it(self):
        df, _cleared = aggregate.apply_reviews(
            self._frame(), {"nairaland-abc123": self._review()})
        self.assertEqual(df.at[0, "sentiment_confidence"], 1.0)
        self.assertEqual(df.at[0, "lga_confidence"], 1.0)

    def test_mentions_false_keeps_the_row_out_of_the_counts(self):
        df, _cleared = aggregate.apply_reviews(
            self._frame(), {"nairaland-abc123": self._review(mentions=False)})
        self.assertEqual(df.at[0, "mentions_candidate_probability"], 0.0)

    def test_a_review_does_not_touch_an_auto_row(self):
        frame = self._frame()
        frame.at[0, "routing_decision"] = "auto"
        df, cleared = aggregate.apply_reviews(
            frame, {"nairaland-abc123": self._review()})
        self.assertEqual(cleared, 0)
        self.assertEqual(df.at[0, "routing_decision"], "auto")
        self.assertEqual(df.at[0, "sentiment_label"], "not_about_candidate")

    def test_no_reviews_changes_nothing(self):
        frame = self._frame()
        df, cleared = aggregate.apply_reviews(frame, {})
        self.assertEqual(cleared, 0)
        self.assertEqual(df.at[0, "sentiment_label"], "not_about_candidate")


class TestMergeCompletedReviews(ReviewQueueTestCase):
    def test_a_dry_run_reports_without_writing(self):
        self.write("queue_a.csv", [row(signed=False)])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        result = reviews.merge_completed_reviews(dry_run=True)
        self.assertEqual(result["merged"], 1)
        self.assertTrue(result["dry_run"])
        body = (self.directory / "queue_a.csv").read_text(encoding="utf-8")
        self.assertNotIn("Bauchi", body, "a dry run wrote to the queue anyway")

    def test_a_real_merge_moves_the_label_into_the_queue(self):
        self.write("queue_a.csv", [row(signed=False)])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        result = reviews.merge_completed_reviews(dry_run=False)
        self.assertEqual(result["merged"], 1)
        found, problems = reviews.load_reviews([self.directory / "queue_a.csv"])
        self.assertEqual(len(found), 1, problems)

    def test_a_merge_never_overwrites_an_existing_label(self):
        # Two reviewers disagreeing is a queue question, not something a merge decides.
        first = row(final_label=label(sentiment="negative"))
        self.write("queue_a.csv", [first])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        result = reviews.merge_completed_reviews(dry_run=False)
        self.assertEqual(result["merged"], 0)
        self.assertEqual(result["already_labelled"], 1)
        found, _problems = reviews.load_reviews([self.directory / "queue_a.csv"])
        self.assertEqual(found["nairaland-abc123"]["sentiment"], "negative")

    def test_a_filled_row_in_no_queue_is_reported_not_inserted(self):
        # It is either a typo or a post nobody asked to review. Inventing a queue row for
        # it would put something in the review record that no reviewer ever saw.
        self.write("queue_a.csv", [])
        self.write("filled/queue_a.csv", [row("nairaland-orphan", final_label=label())])
        result = reviews.merge_completed_reviews(dry_run=False)
        self.assertEqual(result["orphaned"], 1)
        self.assertEqual([p.reason for p in result["problems"]],
                         ["not_in_any_queue"])

    def test_a_started_and_abandoned_review_is_counted_separately(self):
        # A signature with no verdict is not a finished review, and filling in the verdict
        # would mean inventing the reviewer's conclusion. It is also not the same problem as
        # "already done" -- this one is worth going back and finishing.
        self.write("queue_a.csv", [row(signed=True, final_label=None)])
        self.write("filled/queue_a.csv", [row(final_label=label())])
        result = reviews.merge_completed_reviews(dry_run=False)
        self.assertEqual(result["merged"], 0)
        self.assertEqual(result["already_labelled"], 0)
        self.assertEqual(result["incomplete"], 1)
        self.assertEqual([p.reason for p in result["problems"]],
                         ["signature_present_but_no_final_label"])

    def test_a_merge_leaves_an_untouched_row_untouched(self):
        # The 730 rows still waiting for review must come out the other side unchanged, or
        # the merge is destroying work rather than moving it.
        self.write("queue_a.csv",
                   [row(signed=False), row("nairandum-two", signed=False)])
        self.write("filled/queue_a.csv", [row("nairaland-abc123", final_label=label())])
        reviews.merge_completed_reviews(dry_run=False)
        found, problems = reviews.load_reviews([self.directory / "queue_a.csv"])
        self.assertEqual(len(found), 1, problems)
        self.assertEqual(list(found), ["nairaland-abc123"])


class TestTheRealQueuesAreConsistent(unittest.TestCase):
    """Guards on the repository's own review data, not on a fixture."""

    def test_every_queue_id_exists_in_the_classified_set(self):
        import csv as _csv
        classified = set()
        for path in sorted(Path("data/classified").glob("*.csv")):
            if path.name.startswith("pilot"):
                continue
            with path.open(encoding="utf-8", newline="") as handle:
                classified |= {r["raw_id"] for r in _csv.DictReader(handle)}
        queued = set()
        for path in sorted(Path("data/human_review").glob("queue_*.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                queued |= {r["raw_id"] for r in _csv.DictReader(handle)}
        self.assertTrue(queued, "no review queue found; the paths must have moved")
        self.assertEqual(queued - classified, set())

    def test_the_completed_reviews_all_load(self):
        found, problems = reviews.load_reviews()
        self.assertEqual(problems, [], "a completed review in this repository is unusable")
        self.assertGreater(len(found), 0)

    def test_no_reviewed_label_is_outside_the_vocabularies(self):
        found, _problems = reviews.load_reviews()
        for raw_id, review in found.items():
            with self.subTest(raw_id=raw_id):
                self.assertIn(review["sentiment"], reviews.SENTIMENT_LABELS)
                self.assertIn(review["lga"], reviews.REVIEWED_LGA_LABELS)
                self.assertIn(review["language"], reviews.LANGUAGE_LABELS)
                self.assertIn(review["intensity"], reviews.INTENSITY_LEVELS)


if __name__ == "__main__":
    unittest.main()