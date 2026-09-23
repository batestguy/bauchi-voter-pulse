"""Aggregation & prediction (Ph.4). All counting/grouping here in pandas — never in Jev.
Reads data/raw/*.jsonl + data/classified/*.csv, writes data/aggregates/*.csv.
Only candidate-relevant AUTO rows feed LGA/risk outputs (mentions_candidate_probability
>= 0.5, sentiment != not_about_candidate, routing == auto). Low-confidence rows stay
out until a reviewer clears them — never act on them.
Risk model v0 is a versioned transparent heuristic (risk-v0-heuristic + date). An ML
successor (RF/LogReg) activates only when train_risk_model() sees enough LGA-week
history; until then it refuses with a logged reason instead of fitting theater.
Run: python -m src.aggregation.aggregate
"""
import csv
import datetime
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CLASSIFIED_DIR = ROOT / "data" / "classified"
AGG_DIR = ROOT / "data" / "aggregates"
BASELINE = ROOT / "data" / "baseline_lg2026.csv"

RISK_MODEL = "risk-v0-heuristic"
MIN_ROWS_FOR_RATING = 5
MIN_LGA_WEEKS_FOR_ML = 200
SAFE_MAX = 0.3    # neg_share <  SAFE_MAX -> safe
SWING_MAX = 0.5   # <= SWING_MAX -> swing, else at-risk

TOPICS = {
    "healthcare": ["hospital", "clinic", "health", "asibiti", "doctor", "nurse", "vaccin"],
    "roads": ["road", "bridge", "hanya", "hanyoyi"],
    "youth jobs": ["unemployment", "job", "youth", "matasa", "rashin aikin yi", "empowerment"],
    "education": ["school", "teacher", "education", "makaranta", "makarantu", "student"],
    "water": ["water", "borehole", "ruwan sha", "dam"],
    "agriculture": ["fertilizer", "farm", "agriculture", "taki", "manoma", "harvest"],
    "security": ["security", "bandit", "kidnap", "police", "tsaro", "patrol"],
    "markets": ["market", "trader", "price", "kasuwa", "haraji", "stall"],
}


def load_frames():
    raws = []
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    raws.append(json.loads(line))
    raw = pd.DataFrame(raws)
    clfs = []
    for path in sorted(CLASSIFIED_DIR.glob("*.csv")):
        if path.name.startswith("pilot"):
            continue
        clfs.append(pd.read_csv(path, dtype=str))
    clf = pd.concat(clfs, ignore_index=True) if clfs else pd.DataFrame()
    return raw, clf


def tag_topics(df):
    text = df["text"].str.lower().fillna("")
    for topic, keys in TOPICS.items():
        df[f"topic_{topic}"] = text.apply(lambda t, ks=keys: int(any(k in t for k in ks)))
    return df


def main():
    AGG_DIR.mkdir(parents=True, exist_ok=True)
    raw, clf = load_frames()
    if raw.empty or clf.empty:
        print("aggregate: no data")
        return
    clf["parent_id"] = clf["raw_id"].str.split("#").str[0]
    df = clf.merge(raw[["raw_id", "text", "date_scraped", "source"]].rename(
        columns={"raw_id": "parent_id"}), on="parent_id", how="left")
    for col in ["sentiment_confidence", "mentions_candidate_probability",
                "opposition_signal_probability"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["relevant"] = ((df["mentions_candidate_probability"] >= 0.5)
                       & (df["sentiment_label"] != "not_about_candidate"))
    df["usable"] = df["relevant"] & (df["routing_decision"] == "auto")
    df = tag_topics(df)
    today = datetime.date.today().isoformat()

    # LGA x sentiment rollup (usable rows only) -> daily + weekly (7-day window file)
    use = df[df["usable"]].copy()
    grp = (use.groupby(["date_scraped", "lga_relevance_label", "sentiment_label"])
           .agg(mention_count=("raw_id", "count"),
                confidence=("sentiment_confidence", "mean")).reset_index()
           .rename(columns={"date_scraped": "date", "lga_relevance_label": "lga"}))
    grp["confidence"] = grp["confidence"].round(3)
    grp = grp.sort_values(["date", "lga", "sentiment_label"])
    grp.to_csv(AGG_DIR / "lga_daily.csv", index=False)
    grp.to_csv(AGG_DIR / "lga_weekly.csv", index=False)  # single-window for now

    # Topic frequencies among usable rows
    topic_rows = [{"topic": t, "mentions": int(use[f"topic_{t}"].sum()),
                   "neg_share": round(float(use.loc[use[f"topic_{t}"] == 1,
                                                      "sentiment_label"].eq("negative").mean())
                                      if use[f"topic_{t}"].sum() else 0.0, 3)}
                  for t in TOPICS]
    pd.DataFrame(topic_rows).sort_values("mentions", ascending=False).to_csv(
        AGG_DIR / "topics.csv", index=False)

    # Per-LGA topic breakdown (usable rows) -> dashboard top-3 negative topics per LGA
    lt_rows = []
    for lga, g in use.groupby("lga_relevance_label"):
        for t in TOPICS:
            m = int(g[f"topic_{t}"].sum())
            if not m:
                continue
            neg = g.loc[g[f"topic_{t}"] == 1, "sentiment_label"].eq("negative").mean()
            lt_rows.append({"lga": lga, "topic": t, "mentions": m,
                            "neg_share": round(float(neg), 3)})
    (pd.DataFrame(lt_rows, columns=["lga", "topic", "mentions", "neg_share"])
     .sort_values(["lga", "mentions"], ascending=[True, False])
     .to_csv(AGG_DIR / "lga_topics.csv", index=False))

    # Opposition comparison: APM-relevant vs opposition-signal rows (usable only)
    use["opp"] = (use["opposition_signal_probability"] >= 0.5).map({True: "opp_signal",
                                                                    False: "apm_other"})
    opp = (use.groupby("opp").agg(rows=("raw_id", "count"),
                                  neg_share=("sentiment_label",
                                             lambda s: round(float(s.eq("negative").mean()), 3)),
                                  avg_confidence=("sentiment_confidence",
                                                  lambda s: round(float(s.mean()), 3)))
           .reset_index())
    opp.to_csv(AGG_DIR / "opposition.csv", index=False)

    # Risk v0: usable-row volume gate, neg-share bands, narrow-margin penalty.
    base = pd.read_csv(BASELINE, dtype=str).set_index("lga") if BASELINE.exists() else None
    narrow = {"Bogoro", "Dambam", "Zaki"}
    per_lga = use.groupby("lga_relevance_label").agg(
        n=("raw_id", "count"),
        neg_share=("sentiment_label", lambda s: round(float(s.eq("negative").mean()), 3))).reset_index()
    risks = []
    for _, r in per_lga.iterrows():
        if r["n"] < MIN_ROWS_FOR_RATING:
            risks.append((r["lga_relevance_label"], "unrated", "n<5 usable rows"))
            continue
        band = "safe" if r["neg_share"] < SAFE_MAX else (
            "swing" if r["neg_share"] <= SWING_MAX else "at-risk")
        note = f"neg_share={r['neg_share']}"
        if r["lga_relevance_label"] in narrow and r["neg_share"] >= SAFE_MAX and band == "swing":
            band, note = "at-risk", note + " +narrow-margin penalty"
        risks.append((r["lga_relevance_label"], band, note))
    risk_df = pd.DataFrame(risks, columns=["lga", "risk", "signals"])
    risk_df["model_version"] = RISK_MODEL
    risk_df["training_date"] = today
    risk_df["note"] = ("provisional single-window; change-vs-prior activates with >=2 windows; "
                       "baseline votes in data/baseline_lg2026.csv")
    risk_df.sort_values("lga").to_csv(AGG_DIR / "risk.csv", index=False)

    print(f"aggregate: {len(df)} classified, {len(use)} usable "
          f"({len(use)} feed dashboard/risk)")
    print(f"usable by sentiment:\n{use['sentiment_label'].value_counts().to_string()}")
    print(f"risk:\n{risk_df[['lga', 'risk', 'signals']].to_string(index=False)}")


def train_risk_model():
    """ML successor gate. Refuses (with reason) until enough LGA-week history exists."""
    if not (AGG_DIR / "lga_weekly.csv").exists():
        return {"status": "refused", "reason": "no weekly history yet"}
    hist = pd.read_csv(AGG_DIR / "lga_weekly.csv")
    n_weeks = hist["date"].nunique() * hist["lga"].nunique()
    if n_weeks < MIN_LGA_WEEKS_FOR_ML:
        return {"status": "refused",
                "reason": f"only ~{n_weeks} LGA-weeks, need {MIN_LGA_WEEKS_FOR_ML}"}
    raise NotImplementedError("wire RF/LogReg here once the gate passes")


if __name__ == "__main__":
    main()
