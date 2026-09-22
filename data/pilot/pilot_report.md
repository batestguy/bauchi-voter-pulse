# Pilot report — schema v1 (500 synthetic posts, jev-1.13.0, threshold 0.8)

Accuracy vs. template human labels (agreement, not ground truth):

- sentiment: 500/500 = 100.0%
- mentions: 500/500 = 100.0%
- intensity: 345/500 = 69.0%
- lga: 500/500 = 100.0%
- opp: 500/500 = 100.0%
- intensity adjacent (±1 level): 500/500 = 100.0%
- routing: auto 492 (98.4%), human_review 8 (1.6%)

All-5-correct by LGA:
- Alkaleri: 17/25 = 68%
- Bauchi: 18/25 = 72%
- Bogoro: 18/25 = 72%
- Dambam: 18/25 = 72%
- Darazo: 17/25 = 68%
- Dass: 15/25 = 60%
- Gamawa: 18/25 = 72%
- Ganjuwa: 18/25 = 72%
- Giade: 18/25 = 72%
- Itas-Gadau: 14/25 = 56%
- Jamaare: 17/25 = 68%
- Katagum: 20/25 = 80%
- Kirfi: 17/25 = 68%
- Misau: 18/25 = 72%
- Ningi: 17/25 = 68%
- Shira: 17/25 = 68%
- Tafawa-Balewa: 19/25 = 76%
- Toro: 19/25 = 76%
- Warji: 15/25 = 60%
- Zaki: 15/25 = 60%

Routing rule used: auto iff min(sentiment_conf, lga_conf) >= 0.80, else human_review.
Note: template labels are weak (by construction); real validation needs the 100-post weekly human-label loop (Ph.7).

Freeze decision: schema v1 FROZEN. sentiment/mentions/lga/opp at 100% agreement.
Known caveat: intensity exact-level agreement 69% (100% within ±1) — misses are calm↔mild
and moderate↔strong boundary cases. Treat intensity as an ordinal signal; do not claim
exact-level changes on the dashboard without human review. Revisit rubric wording in Ph.7
if weekly human labels confirm the boundary softness.
