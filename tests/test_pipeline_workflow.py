"""The pipeline workflows, and the gap that let the corpus go stale unnoticed.

The pipeline is four steps. `scrape.yml` writes `data/raw/`, `classify_new.py` writes
`data/classified/` and a review queue, `aggregate.py` writes `data/aggregates/`, and
`rebuild-pages.yml` writes `docs/*.html`. The middle two had scripts but **no workflow**,
so the corpus stopped on 23 September 2026 while the page rebuild carried on publishing
every Monday as though it were current. Nothing was red.

These tests assert the wiring, because a missing workflow file produces no failure at all.
That is the whole hazard: a pipeline with a hole in the middle is indistinguishable, from
the outside, from a pipeline that is merely quiet.

The same reasoning covers the specific guards. Each exists for a failure that is invisible
when it happens:
- a review queue that is not staged is human work discarded on the next run;
- a classified set that shrinks commits aggregates that are correctly computed from less
  data, and nothing downstream can tell that from a real week with no news;
- a missing API key is a configuration state, so the run must stay green — but it must also
  say so on the run itself rather than in a log nobody opens.
"""
import re
import unittest
from pathlib import Path


WORKFLOWS = Path(".github/workflows")


def workflow(name: str) -> str:
    path = WORKFLOWS / name
    if not path.exists():
        raise AssertionError(f"{path} does not exist")
    return path.read_text(encoding="utf-8")


class PipelineWorkflowTests(unittest.TestCase):
    def test_every_pipeline_step_has_a_workflow(self):
        # The hole in the middle of the pipeline, asserted by name. A missing file is not
        # a runtime error; it is a step that quietly stops happening.
        for name in ("scrape.yml", "classify.yml", "rebuild-pages.yml"):
            with self.subTest(workflow=name):
                self.assertTrue((WORKFLOWS / name).exists(),
                                f"{name} is missing: its step stops running with no error")

    def test_classification_runs_on_a_schedule_not_only_on_demand(self):
        # `scrape.yml` is workflow_dispatch only, which is a deliberate owner action. This
        # one has to be scheduled or the corpus stops growing on its own.
        source = workflow("classify.yml")
        self.assertIn("schedule:", source)
        self.assertIn("cron:", source)
        self.assertIn("workflow_dispatch:", source)

    def test_classification_uses_the_vendored_client_not_a_registry(self):
        # third_party/jev/jev is committed. An npm install would make the client version
        # something that can drift out from under the schema between two runs of the same
        # spec, and would add a registry dependency to a job that reads the internet once.
        source = workflow("classify.yml")
        self.assertIn("JEV_BIN: third_party/jev/jev", source)
        self.assertTrue(Path("third_party/jev/jev").exists())
        # Assert the absence of the STEP, not of the word. A word-level check fails on the
        # comment explaining why there is no npm install, and would pass on a real install
        # step written the same way.
        for step in re.findall(r"^\s*- run: (.+)$", source, re.M):
            with self.subTest(step=step):
                self.assertNotIn("npm", step)
        for action in re.findall(r"^\s*- uses: (.+)$", source, re.M):
            with self.subTest(action=action):
                self.assertNotIn("npm", action.lower())

    def test_the_api_key_comes_from_a_secret_and_never_from_the_repo(self):
        source = workflow("classify.yml")
        self.assertIn("secrets.TYPESAFE_API_KEY", source)
        # The ignore rule is part of the contract. Without it a pasted key is one
        # `git add .` from being public history.
        ignore = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn("*TYPESAFE*KEY*", ignore)
        self.assertIn("*API_KEY*", ignore)

    def test_a_missing_key_does_not_fail_the_run_but_says_so(self):
        # Green, because a red run for a configuration state trains people to ignore red
        # runs. Visible, because a job that skips itself silently every week is a job
        # nobody notices is broken.
        source = workflow("classify.yml")
        self.assertIn("::warning", source)
        self.assertIn("has_key=false", source)
        self.assertIn("has_key=true", source)
        # The paid step is gated on the key, so a missing secret cannot call the API.
        self.assertRegex(
            source, r"if: steps\.key\.outputs\.has_key == 'true'")

    def test_the_review_queue_is_committed_with_the_classifications(self):
        # classify.py writes each batch's queue into data/human_review/. Not staging it
        # throws away the human work on the next run -- the same class of bug as the one
        # this repository already had, where 160 completed reviews sat in an untracked
        # folder that no code read.
        source = workflow("classify.yml")
        staged = re.search(r"git add (.+)", source)
        self.assertIsNotNone(staged, "the commit step does not stage anything")
        for path in ("data/classified/", "data/aggregates/", "data/human_review/"):
            with self.subTest(path=path):
                self.assertIn(path, staged.group(1))

    def test_a_shrinking_corpus_refuses_to_commit(self):
        # The highest-value guard in the file. A truncated classified set produces
        # aggregates that are correctly computed from less data, and nothing downstream can
        # distinguish that from a genuine quiet week.
        source = workflow("classify.yml")
        self.assertIn("::error", source)
        self.assertIn("pipeline_stats.csv", source)
        self.assertIn("Corpus shrank", source)

    def test_every_writing_job_shares_one_concurrency_group(self):
        # All three push to the index. Two at once race on it, and the loser's push fails
        # in a way that reads as a network problem rather than a concurrency bug. Asserted
        # as EQUALITY, not merely presence: three jobs each with their own group looks
        # correct and serialises nothing. That is the version this file had.
        groups = set()
        for name in ("scrape.yml", "classify.yml", "rebuild-pages.yml"):
            with self.subTest(workflow=name):
                # Comments may sit between the two keys, so the pattern has to tolerate
                # them. A regex that only matches adjacent lines reports "no concurrency
                # group" for a file that has one, which is how a real bug gets dismissed.
                match = re.search(
                    r"concurrency:(?:\n\s*#[^\n]*)*\n\s*group:\s*(\S+)",
                    workflow(name))
                self.assertIsNotNone(match, f"{name} declares no concurrency group")
                groups.add(match.group(1))
        self.assertEqual(len(groups), 1,
                         f"writing jobs use different groups, so they do not serialise: {groups}")
        # Queue rather than cancel: a run that has already paid for classification calls
        # should finish and commit rather than be killed by the next one.
        for name in ("scrape.yml", "classify.yml", "rebuild-pages.yml"):
            with self.subTest(workflow=name):
                self.assertIn("cancel-in-progress: false", workflow(name))

    def test_a_pilot_file_is_never_counted_as_corpus(self):
        # data/classified/pilot_classified.csv is the 500-post calibration run. It is
        # excluded by every reader in the pipeline; a counter that included it would make
        # the shrink guard fire for the wrong reason and teach people to ignore it.
        self.assertIn('startswith("pilot")', workflow("classify.yml"))
        # And the readers themselves must agree, or the guard is measuring a different
        # number from the one the corpus is actually built from.
        for module in ("src/aggregation/aggregate.py", "src/classification/classify_new.py"):
            with self.subTest(module=module):
                self.assertIn('startswith("pilot")',
                              Path(module).read_text(encoding="utf-8"))

    def test_the_local_classifier_and_the_workflow_agree_on_the_venv_free_client(self):
        # classify.py resolves JEV_BIN, defaulting to a PATH `jev`. The workflow points it
        # at the vendored file. If the default ever changed to require an install, the
        # workflow would still work while local runs silently broke.
        source = Path("src/classification/classify.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("JEV_BIN", "jev")', source)


if __name__ == "__main__":
    unittest.main()