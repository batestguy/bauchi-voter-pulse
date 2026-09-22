"""Phase 1 pilot corpus generator (schema v2) — DETERMINISTIC synthetic posts for schema stress-testing.
NOT real scraped data. Every row is marked source=synthetic_pilot. Human labels are assigned
by construction (template intent) so Jev outputs can be scored for agreement.
Strata: 20 LGAs x 25 posts = 500 (per LGA: 12 English / 8 Hausa / 5 mixed).
Hausa templates use simple standard Hausa; real validation needs native-speaker labels (Ph.7)."""
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
TOPICS_HA = {
    "healthcare": "asibiti",
    "roads": "hanyoyi",
    "youth jobs": "rashin aikin yi ga matasa",
    "education": "makarantu",
    "water": "ruwan sha",
    "agriculture": "takin zamani",
    "security": "tsaro",
    "markets": "harajin kasuwa",
}

# (template, intensity) pools per language x bucket. mention/opp set by bucket.
EN = {
    "pos": [
        ("Yakubu Adamu commissioned a new {topic} in {lga} today, residents are celebrating.", "mild"),
        ("APM's {topic} programme in {lga} is working. Kudos to Yakubu Adamu!", "moderate"),
        ("Good news from {lga}: {topic} has improved under the APM government.", "calm"),
    ],
    "neg": [
        ("APM has failed {lga} on {topic}. Yakubu Adamu must act now.", "moderate"),
        ("No {topic} in {lga} for months! This APM government does not care about us at all!", "strong"),
        ("{Lga} people are suffering over {topic} while Yakubu Adamu makes empty promises.", "moderate"),
    ],
    "neg_opp": [
        ("APM has failed {lga} on {topic}. PDP will take back our communities next year.", "strong"),
        ("Yakubu Adamu cannot fix {topic} in {lga}. APC has the real blueprint for Bauchi.", "moderate"),
    ],
    "neu": [
        ("Yakubu Adamu visited {lga} yesterday to inspect {topic} projects.", "calm"),
        ("APM announced a committee on {topic} covering {lga} and neighbouring areas.", "calm"),
    ],
    "not": [
        ("Rainfall in {lga} this season is good for the farms.", "calm"),
        ("Football: {lga} united drew 1-1 on Sunday, fans want a bigger stadium.", "mild"),
        ("Traders in {lga} market complain about rising prices of goods.", "mild"),
    ],
}
HA = {
    "pos": [
        ("Yakubu Adamu ya kaddamar da sabuwar {topic_ha} a {lga}, al'umma suna murna.", "mild"),
        ("Shirin {topic_ha} na APM a {lga} yana aiki. Madalla da Yakubu Adamu!", "moderate"),
    ],
    "neg": [
        ("APM ta gaza a {lga} kan {topic_ha}. Ya kamata mu kori gwamnatin APM!", "moderate"),
        ("Babu {topic_ha} a {lga} tun da dadewa! Gwamnatin APM ba ta damu da mu ba!", "strong"),
    ],
    "neg_opp": [
        ("APM ta gaza a {lga} kan {topic_ha}. PDP za ta dawo mulki nan gaba.", "strong"),
        ("Yakubu Adamu ba zai iya gyara {topic_ha} a {lga} ba. APC ce ke da sahihin tsari.", "moderate"),
    ],
    "neu": [
        ("Yakubu Adamu ya ziyarci {lga} jiya don duba ayyukan {topic_ha}.", "calm"),
    ],
    "not": [
        ("Ruwan sama a {lga} bana yana da kyau ga manoma.", "calm"),
        ("Yan kasuwa a {lga} suna korafin tsadar kayayyaki.", "mild"),
    ],
}
MIX = {
    "pos": [
        ("Good news daga {lga}: {topic} ya inganta karkashin APM.", "mild"),
        ("Yakubu Adamu is doing great work, {topic_ha} ta inganta a {lga}.", "moderate"),
    ],
    "neg": [
        ("APM has failed {lga} on {topic}, talakawa suna shan wahala.", "moderate"),
        ("Babu {topic} in {lga} karkashin APM, this government does not care about talakawa!", "strong"),
    ],
    "neg_opp": [
        ("PDP za ta take over {lga} next year, APM ta gaza. Muna goyon bayan PDP.", "strong"),
    ],
    "neu": [
        ("Yakubu Adamu ya ziyarci {lga} yesterday don duba projects.", "calm"),
    ],
    "not": [
        ("Match na {lga} united ya kare 1-1 on Sunday.", "calm"),
    ],
}
BUCKETS = {"pos": ("positive", 1, 0), "neg": ("negative", 1, 0),
           "neg_opp": ("negative", 1, 1), "neu": ("neutral", 1, 0), "not": ("not_about_candidate", 0, 0)}
# No-LGA texts (no {lga} slot): human_lga_relevance = "unclear". (lang, bucket, count)
NOLGA_PLAN = ([("english", "not")] * 12 + [("english", "neu")] * 4
              + [("hausa", "not")] * 8 + [("hausa", "neu")] * 4
              + [("mixed", "not")] * 8 + [("mixed", "neu")] * 4)
NOLGA = {
    "english": {
        "not": ["Rainfall this season is good for farmers nationwide.",
                "The Super Eagles play on Sunday and fans are excited.",
                "Traders everywhere complain about rising prices of goods."],
        "neu": ["Yakubu Adamu announced a statewide empowerment programme today.",
                "APM released its campaign schedule for the coming weeks."],
    },
    "hausa": {
        "not": ["Ruwan sama bana yana da kyau ga manoma a fadin kasa.",
                "Yan kasuwa suna korafin tsadar kayayyaki ko ina."],
        "neu": ["Yakubu Adamu ya sanar da sabon shiri a fadin jihar."],
    },
    "mixed": {
        "not": ["Match ya kare 1-1 on Sunday, fans suna murna.",
                "Prices are rising, talakawa suna shan wahala."],
        "neu": ["Yakubu Adamu ya sanar da new programme today."],
    },
}
# per-LGA plan: (lang, bucket, count)
PLAN = [("english", "pos", 3), ("english", "neg", 2), ("english", "neg_opp", 1),
        ("english", "neu", 2), ("english", "not", 4),
        ("hausa", "pos", 2), ("hausa", "neg", 2), ("hausa", "neg_opp", 1),
        ("hausa", "neu", 1), ("hausa", "not", 2),
        ("mixed", "pos", 1), ("mixed", "neg", 1), ("mixed", "neg_opp", 1),
        ("mixed", "neu", 1), ("mixed", "not", 1)]
POOLS = {"english": EN, "hausa": HA, "mixed": MIX}


def build():
    rng = random.Random(2027)
    rows = []
    n = 0
    topic_keys = sorted(TOPICS)
    for lga in LGAS:
        for lang, bucket, count in PLAN:
            sentiment, mention, opp = BUCKETS[bucket]
            pool = POOLS[lang][bucket]
            for i in range(count):
                n += 1
                template, intensity = pool[(i + rng.randrange(len(pool))) % len(pool)]
                tk = rng.choice(topic_keys)
                text = template.format(topic=TOPICS[tk], topic_ha=TOPICS_HA[tk],
                                       lga=lga, Lga=lga, Topic=TOPICS[tk].capitalize())
                rows.append({
                    "raw_id": f"PILOT-{n:04d}",
                    "source": "synthetic_pilot",
                    "text": text,
                    "human_sentiment": sentiment,
                    "human_mentions_candidate": mention,
                    "human_intensity": intensity,
                    "human_lga_relevance": lga,
                    "human_opposition": opp,
                    "human_language": lang,
                })
    for lang, bucket in NOLGA_PLAN:
        sentiment, mention, opp = BUCKETS[bucket]
        pool = NOLGA[lang][bucket]
        template = pool[n % len(pool)]
        tk = topic_keys[n % len(topic_keys)]
        n += 1
        rows.append({
            "raw_id": f"PILOT-{n:04d}",
            "source": "synthetic_pilot",
            "text": template.format(topic=TOPICS[tk], topic_ha=TOPICS_HA[tk]),
            "human_sentiment": sentiment,
            "human_mentions_candidate": mention,
            "human_intensity": "calm",
            "human_lga_relevance": "unclear",
            "human_opposition": opp,
            "human_language": lang,
        })
    assert len(rows) == 540, len(rows)
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
