# Pilot report — schema v3 (540 synthetic: 256 EN / 172 HA / 112 mixed, incl. 40 no-LGA, jev-1.13.0, threshold 0.8)

Accuracy vs. template human labels (agreement, not ground truth):

- sentiment: 538/540 = 99.6%
- mentions: 540/540 = 100.0%
- intensity: 269/540 = 49.8%
- lga: 527/540 = 97.6%
- opp: 540/540 = 100.0%
- language: 512/540 = 94.8%
- intensity adjacent (±1 level): 502/540 = 93.0%
- routing: auto 427 (79.1%), human_review 113 (20.9%)

Sentiment accuracy + review rate by language:
- english: sentiment 100.0%, review rate 3.9% (n=256)
- hausa: sentiment 98.8%, review rate 44.2% (n=172)
- mixed: sentiment 100.0%, review rate 24.1% (n=112)

All-5-correct (excl. language) by LGA:
- Alkaleri: 14/25 = 56%
- Bauchi: 6/25 = 24%
- Bogoro: 12/25 = 48%
- Dambam: 13/25 = 52%
- Darazo: 10/25 = 40%
- Dass: 14/25 = 56%
- Gamawa: 16/25 = 64%
- Ganjuwa: 12/25 = 48%
- Giade: 12/25 = 48%
- Itas-Gadau: 15/25 = 60%
- Jamaare: 12/25 = 48%
- Katagum: 13/25 = 52%
- Kirfi: 15/25 = 60%
- Misau: 14/25 = 56%
- Ningi: 14/25 = 56%
- Shira: 14/25 = 56%
- Tafawa-Balewa: 8/25 = 32%
- Toro: 8/25 = 32%
- Warji: 13/25 = 52%
- Zaki: 12/25 = 48%
- unclear: 16/40 = 40%

Routing rule used: auto iff min(sentiment_conf, lga_conf) >= 0.80, else human_review.
Note: template labels are weak (by construction, simple standard Hausa); real validation needs native-speaker labels in the 100-post weekly loop (Ph.7).

Freeze decision: schema v3 FROZEN (supersedes v2).
- sentiment 99.6% / mentions 100% / opp 100% / lga 97.6% / language 94.8%.
- unclear fallback verified: off-topic real-world post → unclear @1.0; named-LGA posts unaffected.
  Known boundary: bare state-level "Bauchi" (no city context) → unclear. Safe direction — keeps
  state-level news out of Bauchi LGA. All 13 lga misses are this case.
- intensity exact 49.8% (93.0% within ±1): ordinal signal only, unchanged caveat.
- Hausa review rate 44.2% vs English 3.9%: unchanged finding, unchanged staffing implication.
- All-5-correct per LGA is intensity-noise-dominated; track per-question accuracy instead.
