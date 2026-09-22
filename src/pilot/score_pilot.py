"""Score Phase 1 pilot: join human labels with Jev outputs, accuracy per question + LGA,
routing split, and classified CSV in AGENTS.md columns. Run: python src/pilot/score_pilot.py"""
import csv
import json
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "pilot" / "pilot_500.jsonl"
JEV = ROOT / "data" / "pilot" / "jev_out.jsonl"
REPORT = ROOT / "data" / "pilot" / "pilot_report.md"
CLASSIFIED = ROOT / "data" / "classified" / "pilot_classified.csv"
THRESHOLD = 0.80
SCHEMA_VERSION = "v1"
MODEL = "jev-1.13.0"


def main():
    humans = [json.loads(l) for l in PILOT.open(encoding="utf-8")]
    jevs = [json.loads(l) for l in JEV.open(encoding="utf-8")]
    assert len(humans) == len(jevs) == 500
    stats = Counter()
    by_lga = defaultdict(Counter)
    routing = Counter()
    intensity_adj = 0
    order = ["calm", "mild", "moderate", "strong", "very_strong"]
    rows = []
    for h, j in zip(humans, jevs):
        a = j["answers"]
        pred = {
            "sentiment": a["sentiment"]["choice"],
            "mentions": int(a["mentions_candidate"]["yes"]),
            "intensity": a["intensity"]["label"],
            "lga": a["lga_relevance"]["choice"],
            "opp": int(a["opposition_signal"]["yes"]),
        }
        s_conf = a["sentiment"]["confidence"]
        l_conf = a["lga_relevance"]["confidence"]
        decision = "auto" if min(s_conf, l_conf) >= THRESHOLD else "human_review"
        routing[decision] += 1
        checks = {
            "sentiment": pred["sentiment"] == h["human_sentiment"],
            "mentions": pred["mentions"] == h["human_mentions_candidate"],
            "intensity": pred["intensity"] == h["human_intensity"],
            "lga": pred["lga"] == h["human_lga_relevance"],
            "opp": pred["opp"] == h["human_opposition"],
        }
        for k, ok in checks.items():
            stats[f"{k}_ok"] += ok
            stats[f"{k}_n"] += 1
        if abs(order.index(pred["intensity"]) - order.index(h["human_intensity"])) <= 1:
            intensity_adj += 1
        lga = h["human_lga_relevance"]
        by_lga[lga]["n"] += 1
        by_lga[lga]["ok"] += all(checks.values())
        rows.append({
            "raw_id": h["raw_id"], "sentiment_label": pred["sentiment"],
            "sentiment_confidence": round(s_conf, 3),
            "mentions_candidate_probability": round(a["mentions_candidate"]["noul"], 3),
            "intensity_score": pred["intensity"],
            "lga_relevance_label": pred["lga"], "lga_confidence": round(l_conf, 3),
            "opposition_signal_probability": round(a["opposition_signal"]["noul"], 3),
            "routing_decision": decision, "schema_version": SCHEMA_VERSION, "model": MODEL,
        })
    CLASSIFIED.parent.mkdir(parents=True, exist_ok=True)
    with CLASSIFIED.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    L = [f"# Pilot report — schema v1 (500 synthetic posts, {MODEL}, threshold {THRESHOLD})",
         "", "Accuracy vs. template human labels (agreement, not ground truth):", ""]
    for k in ["sentiment", "mentions", "intensity", "lga", "opp"]:
        L.append(f"- {k}: {stats[f'{k}_ok']}/{stats[f'{k}_n']} = {stats[f'{k}_ok']/stats[f'{k}_n']:.1%}")
    L += [f"- intensity adjacent (±1 level): {intensity_adj}/500 = {intensity_adj/500:.1%}",
          f"- routing: auto {routing['auto']} ({routing['auto']/5:.1f}%), human_review {routing['human_review']} ({routing['human_review']/5:.1f}%)",
          "", "All-5-correct by LGA:"]
    for lga in sorted(by_lga):
        c = by_lga[lga]
        L.append(f"- {lga}: {c['ok']}/{c['n']} = {c['ok']/c['n']:.0%}")
    L += ["", "Routing rule used: auto iff min(sentiment_conf, lga_conf) >= 0.80, else human_review.",
          "Note: template labels are weak (by construction); real validation needs the 100-post weekly human-label loop (Ph.7)."]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:9]))
    print(f"wrote {REPORT} + {CLASSIFIED}")


if __name__ == "__main__":
    main()
