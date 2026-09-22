"""Phase 1 pilot corpus generator — DETERMINISTIC synthetic posts for schema stress-testing.
NOT real scraped data. Every row is marked source=synthetic_pilot. Human labels are assigned
by construction (template intent) so Jev outputs can be scored for agreement.
Strata: 20 LGAs x 25 posts = 500. Mix per LGA: 8 pos / 8 neg / 4 neutral / 5 not-about-candidate."""
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "pilot" / "pilot_500.jsonl"

LGAS = ["Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
        "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi",
        "Misau", "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"]

TOPICS = {
    "healthcare": "primary healthcare centre",
    "roads": "rural road repairs",
    "youth jobs": "youth unemployment",
    "education": "primary school renovation",
    "water": "clean water supply",
    "agriculture": "fertilizer distribution",
    "security": "night patrols and security",
    "markets": "market stall fees",
}

POS_T = [
    ("Yakubu Adamu commissioned a new {topic} in {lga} today, residents are celebrating.", "mild"),
    ("APM's {topic} programme in {lga} is working. Kudos to Yakubu Adamu!", "moderate"),
    ("I am so happy! {Lga} is finally seeing real progress on {topic} because of Dr. Yakubu Adamu. APM forever!", "strong"),
    ("Good news from {lga}: {topic} has improved under the APM government.", "calm"),
]
NEG_T = [
    ("APM has failed {lga} on {topic}. Yakubu Adamu must act now.", "moderate"),
    ("No {topic} in {lga} for months! This APM government does not care about us at all!", "strong"),
    ("{Lga} people are suffering over {topic} while Yakubu Adamu makes empty promises.", "moderate"),
    ("DISASTER in {lga}!!! {Topic} has collapsed and APM is silent! Enough is enough!", "very_strong"),
]
NEG_OPP_T = [
    ("APM has failed {lga} on {topic}. PDP will take back our communities next year.", "strong"),
    ("Yakubu Adamu cannot fix {topic} in {lga}. APC has the real blueprint for Bauchi.", "moderate"),
]
NEU_T = [
    ("Yakubu Adamu visited {lga} yesterday to inspect {topic} projects.", "calm"),
    ("APM announced a committee on {topic} covering {lga} and neighbouring areas.", "calm"),
]
NOT_ABOUT_T = [
    ("Rainfall in {lga} this season is good for the {topic} farms.", "calm"),
    ("Football: {lga} united drew 1-1 on Sunday, fans want better {topic} at the stadium.", "mild"),
    ("Traders in {lga} market complain about rising prices of goods.", "mild"),
]


def build():
    rng = random.Random(2026)
    rows = []
    n = 0
    for lga in LGAS:
        lga_cap = lga
        batch = []
        for t, inten in POS_T * 2:
            batch.append(("positive", 1, inten, lga, 0, t))
        for t, inten in NEG_T[:2] * 2:
            batch.append(("negative", 1, inten, lga, 0, t))
        for t, inten in NEG_OPP_T * 2:
            batch.append(("negative", 1, inten, lga, 1, t))
        for t, inten in NEU_T * 2:
            batch.append(("neutral", 1, inten, lga, 0, t))
        for t, inten in NOT_ABOUT_T:
            batch.append(("not_about_candidate", 0, inten, lga, 0, t))
        # 8+4+4+4+3 = 23 -> top up to 25 with shuffled extras
        while len(batch) < 25:
            batch.append(rng.choice(batch))
        rng.shuffle(batch)
        for sentiment, mention, intensity, lga_label, opp, template in batch[:25]:
            n += 1
            topic_key = rng.choice(sorted(TOPICS))
            topic = TOPICS[topic_key]
            text = template.format(topic=topic, lga=lga, Lga=lga_cap, Topic=topic.capitalize())
            rows.append({
                "raw_id": f"PILOT-{n:04d}",
                "source": "synthetic_pilot",
                "text": text,
                "human_sentiment": sentiment,
                "human_mentions_candidate": mention,
                "human_intensity": intensity,
                "human_lga_relevance": lga_label,
                "human_opposition": opp,
            })
    assert len(rows) == 500, len(rows)
    return rows


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build()
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
