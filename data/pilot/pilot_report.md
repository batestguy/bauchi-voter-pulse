# Pilot report — schema v2 (500 synthetic posts: 240 EN / 160 HA / 100 mixed, jev-1.13.0, threshold 0.8)

Accuracy vs. template human labels (agreement, not ground truth):

- sentiment: 498/500 = 99.6%
- mentions: 500/500 = 100.0%
- intensity: 253/500 = 50.6%
- lga: 500/500 = 100.0%
- opp: 500/500 = 100.0%
- language: 469/500 = 93.8%
- intensity adjacent (±1 level): 461/500 = 92.2%
- routing: auto 416 (83.2%), human_review 84 (16.8%)

Sentiment accuracy + review rate by language:
- english: sentiment 100.0%, review rate 0.8% (n=240)
- hausa: sentiment 98.8%, review rate 41.2% (n=160)
- mixed: sentiment 100.0%, review rate 16.0% (n=100)

All-5-correct (excl. language) by LGA:
- Alkaleri: 13/25 = 52%
- Bauchi: 12/25 = 48%
- Bogoro: 12/25 = 48%
- Dambam: 13/25 = 52%
- Darazo: 11/25 = 44%
- Dass: 14/25 = 56%
- Gamawa: 17/25 = 68%
- Ganjuwa: 13/25 = 52%
- Giade: 12/25 = 48%
- Itas-Gadau: 14/25 = 56%
- Jamaare: 11/25 = 44%
- Katagum: 13/25 = 52%
- Kirfi: 15/25 = 60%
- Misau: 14/25 = 56%
- Ningi: 12/25 = 48%
- Shira: 15/25 = 60%
- Tafawa-Balewa: 9/25 = 36%
- Toro: 8/25 = 32%
- Warji: 14/25 = 56%
- Zaki: 11/25 = 44%

Routing rule used: auto iff min(sentiment_conf, lga_conf) >= 0.80, else human_review.
Note: template labels are weak (by construction, simple standard Hausa); real validation needs native-speaker labels in the 100-post weekly loop (Ph.7).

Freeze decision: schema v2 FROZEN (supersedes v1).
- sentiment 99.6% / mentions 100% / lga 100% / opp 100% / language 93.8% (all 31 misses are
  mixed→hausa: soft boundary, safe direction — a Hausa-capable reviewer still handles them).
- intensity exact 50.6% (92.2% within ±1): ordinal signal only, no exact-level dashboard claims.
- Headline operational finding: Hausa review rate 41.2% vs English 0.8%. Jev reads Hausa
  correctly (98.8% sentiment) but with lower confidence. Staff Hausa-capable reviewers;
  never lower the threshold to compensate. Report per-language review rates in every eval.
- Residual errors (2 Hausa sentiment flips, both conf ≤0.58) were correctly routed to review.
- Known discourse trait: Hausa criticism is often indirect ("ya kamata ya yi aiki" softens
  blame) — train reviewers on this; it inflates the Hausa review queue by design.
