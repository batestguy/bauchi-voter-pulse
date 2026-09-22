# Human review queue — protocol (non-negotiable)

1. Work only from `queue_*.csv`. Never act on a row with `routing_decision = human_review`
   (min of sentiment/lga confidence < 0.80) without logging it here first.
2. For each row fill: `reviewer_label` (correct sentiment), `final_label` (label to use
   downstream), and `reviewer_reasoning` (1–2 sentences: what Jev got wrong and why).
   Sign with `reviewed_by` + `reviewed_at`.
3. Language notes: Hausa posts dominate this queue (~41% review rate vs ~1% English).
   Hausa criticism is often indirect ("ya kamata ya yi aiki" softens blame) — read the
   whole post before overriding. Mixed↔Hausa boundary is soft; either label is acceptable
   if you note it.
4. Intensity is ordinal noise (±1 level): correct only clear misses, don't fine-tune levels.
5. Every override feeds schema improvement — vague reasoning ("looks wrong") is rejected.
   Eval role reviews this log weekly and may pause classification over patterns.
