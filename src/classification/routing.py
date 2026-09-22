"""Confidence routing — the non-negotiable gate (AGENTS.md).
Rule: auto iff min(sentiment_confidence, lga_confidence) >= threshold, else human_review.
Language confidence is measured, never gated. Never act on low-confidence rows.
"""
THRESHOLD = 0.80
SCHEMA_VERSION = "v2"


def apply_routing(sentiment_confidence, lga_confidence, threshold=THRESHOLD):
    if min(float(sentiment_confidence), float(lga_confidence)) >= float(threshold):
        return "auto"
    return "human_review"


REVIEW_COLUMNS = [
    "raw_id", "text", "sentiment_label", "sentiment_confidence",
    "mentions_candidate_probability", "intensity_score",
    "lga_relevance_label", "lga_confidence", "opposition_signal_probability",
    "language_label", "language_confidence", "schema_version", "model",
    "reviewer_label", "reviewer_reasoning", "final_label", "reviewed_by", "reviewed_at",
]
