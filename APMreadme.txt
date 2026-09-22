Bauchi Voter Pulse
Final Build Framework & Agent Operations Manual
Prepared for: APM Bauchi Governorship Campaign Team
Purpose: A data-driven public sentiment and voter intelligence system for the 2027 Bauchi governorship election
Version: 1.0 — Final Consolidated Framework

1. Executive Summary
Bauchi Voter Pulse is a live sentiment and voter intelligence dashboard that scrapes public Nigerian political discourse, classifies it using the Jev TypeSafe decision model, and presents LGA-level insights to the APM campaign team. It runs entirely on free tools, requires no paid infrastructure, and delivers one actionable insight per week to the campaign's decision-makers.

The system has three layers: Ingestion (scraping public text), Classification (Jev-typed sentiment and topic labelling with calibrated probabilities), and Aggregation & Prediction (LGA-level risk classification and dashboard delivery). Six agent roles operate the system. The campaign team receives a single shareable link that updates weekly.

2. System Architecture
Layer 1: Ingestion
Collects raw text from four free sources:

Source	What Is Scraped	Frequency
Nairaland Politics	Thread titles, post bodies, timestamps, view/reply counts	Daily
Nigerian news sites (Punch, Vanguard, Daily Post, The Cable, Tribune)	Headlines, article bodies, publication dates, source	Daily
Public Facebook pages (Bauchi political groups, news outlets)	Post text, reaction counts, comment counts, share counts	Daily
Bauchi State budget documents (bauchistate.gov.ng)	Budget tables, revenue projections, sector allocations	Monthly
Standardized output: raw_id, source, date_scraped, text, url, lga_keyword_match

Ingestion rules:

Scrape only public data. Never scrape private groups or DMs.

Respect robots.txt and add rate-limit delays.

Anonymize usernames — store sentiment and topic data, not identifiable user profiles.

Never modify scraped text. Store exactly what was collected.

Layer 2: Classification (Jev)
Applies Jev, TypeSafe AI's System One decision model, to the standardized raw table. Jev returns typed answers with calibrated probabilities rather than generated text.

Three question primitives:

Primitive	Function	Returns
Choice	Pick one option from a predefined set (up to 255 options)	Label + probability per option + confidence
Score	Rate against ordered rubric levels (up to 10)	Probability-weighted value + full distribution
Noul	Yes/no decision	Probability it is true
All questions are evaluated in parallel in a single API call. A single call can extract sentiment, candidate mention, intensity, LGA relevance, and opposition signal simultaneously.

Core question schema:

Question	Primitive	Purpose
sentiment	Choice	Positive / Negative / Neutral / Not about candidate
mentions_candidate	Noul	Does text mention Dr. Yakubu Adamu or APM campaign?
intensity	Score	Calm → Mild → Moderate → Strong → Very strong
lga_relevance	Choice	Which Bauchi LGA is this most relevant to?
opposition_signal	Noul	Does text appear to originate from PDP or APC sympathizers?
Standardized output: raw_id, sentiment_label, sentiment_confidence, mentions_candidate_probability, intensity_score, lga_relevance_label, opposition_signal_probability, routing_decision

Confidence routing (non-negotiable):

Confidence ≥ 0.80 → auto-processed

Confidence < 0.80 → routed to human review

Layer 3: Aggregation & Prediction
Groups classified rows by LGA, date, and topic. Computes daily sentiment totals, average confidence, and topic frequencies. Trains a lightweight predictive model (Random Forest or Logistic Regression) using Jev labels as features to produce LGA-level risk classifications.

Prediction target: Change from the LG election baseline, not the baseline itself. The APM won all 20 LGAs in August 2026, with vote counts ranging from 19,730 (Dambam) to 125,170 (Bauchi). The model must detect shifts — especially in narrow-margin LGAs (Bogoro 25,282; Dambam 19,730; Zaki 19,984).

Standardized output: Daily/weekly LGA aggregates, topic frequency tables, opposition comparison metrics, LGA risk labels (safe / swing / at-risk).

3. Agent Roles and Responsibilities
Role 1: Data Ingestion Agent
Owns all scraping and data collection. Builds and maintains scrapers per source, schedules daily runs via GitHub Actions (free tier), handles rate limits and robots.txt, deduplicates raw records, and maintains raw_id integrity across all sources.

Rule: Never modify scraped text. Store exactly what was collected.

Role 2: Question Schema Agent
Owns the Jev question definitions. Defines Choice, Score, and Noul questions once and versions them. No other agent may change question wording.

Rules: Every question must be atomic (one dimension per question). Choice options must be mutually exclusive. Score rubrics must be ordered correctly. Schema version must be stored alongside every classified row.

Role 3: Classification Agent
Runs the Jev classification pipeline. Batches raw records into Jev calls, handles the 32K token context limit by chunking long threads, manages API rate limits (250,000 tokens/second, 1,200 requests/minute), and applies the confidence routing logic.

Rule: Never act on a Jev decision below the confidence threshold. Low-confidence rows are flagged for human review.

Role 4: Aggregation and Prediction Agent
Produces dashboard-ready aggregates and predictive outputs. Owns daily/weekly LGA aggregation, topic frequency analysis, opposition comparison metrics, and the LGA risk classifier.

Rule: Document the model version and training date for every prediction.

Role 5: Evaluation and Quality Agent
Runs the weekly evaluation cycle. Samples 100 classified posts per week, manually labels them, compares Jev labels against human labels, calculates accuracy by question and by LGA, and flags when accuracy drops below acceptable thresholds. Also tests adversarial inputs.

Authority: Can pause classification and escalate to the schema agent for question revision.

Role 6: Delivery Agent
Owns the dashboard and briefing outputs. Maintains the dashboard, generates the weekly one-page briefing template, and ensures the campaign team can access the latest outputs via a single shared link.

Rule: Does not modify data — presents what the other agents produce.

4. Dashboard and Sharing Options
The campaign needs a shareable dashboard that updates weekly. Four options are available, ranked by ease of implementation.

Option A: Google Looker Studio + Google Sheets (Recommended — Easiest)
How it works: A Google Sheet holds the aggregated data. Looker Studio connects to that Sheet and automatically reflects whatever is in it. The campaign team gets a single shareable link. No coding, no hosting, no deployment.

One-time setup:

Create a Google Sheet with one tab. Row 1 = column headers (date, lga, sentiment_label, mention_count, confidence). Data starts at A1. No merged cells, no blank rows above headers.

Open lookerstudio.google.com, create a blank report, connect to the Sheet.

Build visualizations — LGA heatmap, sentiment trend line, opposition comparison table. Drag and drop only.

Set Data Freshness for the Sheet connector (default: hourly).

Share the report link set to "Anyone with the link can view."

Weekly update cycle: Run the pipeline. Aggregate results into the same column structure. Paste new data over old data in the Sheet. Dashboard updates automatically. No republishing.

Trade-off: Less flexible for custom NLP visuals. Large datasets can get sluggish.

Best for: A non-technical campaign staffer who needs to update the dashboard by uploading a new CSV or pasting into a Sheet each week.

Option B: Datawrapper (Easiest for Maps and Charts Only)
How it works: Datawrapper creates maps, charts, and tables with no coding. Connects to a live Google Sheet or CSV URL and updates automatically. Free tier updates every minute for the first 24 hours, then hourly for 29 days.

One-time setup: Publish a chart connected to a Google Sheet. Set the Sheet as the live data source.

Weekly update cycle: Overwrite the Google Sheet. The chart updates on its own. Share the chart's embed link or public URL.

Trade-off: Not a full dashboard — a collection of individual visualizations.

Best for: A campaign that primarily needs a shareable LGA map and a sentiment trend chart.

Option C: Panel on Hugging Face Spaces (Python Control)
How it works: Panel is an open-source Python dashboard library. Hugging Face Spaces hosts Panel apps for free. Create a Space, upload app.py, requirements.txt, and a Dockerfile. The Space builds and runs automatically.

One-time setup: Build the Panel app in Python. Create a Hugging Face Space. Upload the files. Share the Space URL.

Weekly update cycle: Hugging Face Spaces does not auto-re-run code on a schedule. Options:

Upload a new version of the app with updated data baked in, or

Use persistent storage and have the pipeline write new data there, or

Set up GitHub Actions to push updated data files to the Space repository on a weekly cron.

Trade-off: More work than Looker Studio. Gives full Python control over visualizations.

Best for: Someone comfortable with Python who wants a live, interactive dashboard with custom Plotly or Folium maps.

Option D: GitHub Pages (Fully Automated, Hands-Off)
How it works: The Python pipeline generates a static HTML dashboard file. GitHub Actions runs on a weekly cron, regenerates the HTML, and commits it to the repository. GitHub Pages serves the committed HTML at a public URL.

One-time setup: Configure the pipeline to output a static HTML dashboard. Set up a GitHub Actions workflow with a weekly cron. Enable GitHub Pages on the repository.

Weekly update cycle: Fully automated. GitHub Actions triggers the pipeline. The pipeline regenerates the dashboard HTML. The commit pushes the new file. The live URL shows the updated dashboard. No human touches anything.

Trade-off: Most technically involved to set up. Least ongoing effort once configured.

Best for: A campaign that wants a dashboard that rebuilds itself weekly with zero manual intervention.

Dashboard Options Comparison
Option	Coding Required	Weekly Update Effort	Sharing Method	Best For
Looker Studio + Sheets	None	Paste new data into Sheet	Share link	Non-technical staff
Datawrapper	None	Overwrite Google Sheet	Chart embed link	Maps and charts only
Panel + Hugging Face	Python	Push updated data or re-deploy	Space URL	Python control
GitHub Pages	Python + Actions	Fully automated	Pages URL	Hands-off automation
Recommendation: Start with Looker Studio + Google Sheets. It is the single easiest path to a shareable, weekly-updating dashboard. If the campaign later needs more interactivity, migrate to Panel on Hugging Face Spaces. If they need a fully automated, hands-off system, move to GitHub Pages.

5. Key Design Principles
Jev is a decision system, not a classifier. The probability and confidence values are the product. A "positive" label at 0.52 confidence is not the same as one at 0.94 confidence. Treat low-confidence decisions as signals to investigate, not facts to act on.

Parallel question evaluation is the core efficiency. A single Jev call evaluates all questions simultaneously. Cost per post is driven by input tokens alone, not by the number of questions asked. Input pricing is $0.042 per million tokens; output is free. Jev is reported to be up to 193.6× faster and 444.6× cheaper than frontier LLMs on comparable workflow evaluations, with 70–500ms end-to-end latency.

The LGA heatmap is the primary artifact. The campaign team does not need sentiment distributions or confidence histograms. They need a map of Bauchi's 20 LGAs coloured by sentiment intensity, with click-through to the top three topics driving negative sentiment per LGA. Everything else supports that one view.

Opposition monitoring must use the identical pipeline. Running the same Jev questions on APM, PDP, and APC mentions ensures comparability. If the schema changes for one, it must change for all.

Confidence routing is non-negotiable. A political campaign cannot afford to act on ambiguous signals. High-confidence decisions auto-process; low-confidence decisions escalate to human review. Reviewers must record reasoning for every override — these become training data for schema improvement.

Jev is not a counting machine. Jev is unstable on arithmetic, counting, dates, literal matching, irrelevant information, and adversarial inputs. All counting happens in the aggregation layer using standard data tools. Jev labels the posts; pandas counts them.

Version everything. Question schema version, model version (jev-1.13.0 or jev-latest), routing threshold, and aggregation logic must be logged alongside every output. When the campaign asks "why did the dashboard say Ningi was at-risk last week?", the agent must trace the answer back to the exact schema, model, and data.

The framework is a loop, not a pipeline. Evaluation findings feed back into schema revisions, which feed back into routing thresholds, which feed back into the risk model. The first version will be imperfect. The tenth version will be a competitive advantage.

6. Known Limitations of Jev (Documented for Agents)
Limitation	Campaign Implication	Mitigation
No text generation	Cannot write briefings or summaries	Use a separate LLM for narrative generation
Unstable on arithmetic/counting	Cannot reliably count mentions or calculate percentages	Do counting in pandas
Unstable on dates	Cannot reliably parse "last week" or "October 2026"	Extract dates with regex before Jev
Unstable on adversarial inputs	Opposition may deliberately confuse classifier	Human review for low-confidence rows
32K token context limit	Cannot process extremely long threads in one call	Chunk long threads or process post-by-post
Text input only	Cannot process images or video	Use separate image analysis tools
No named entity recognition	Cannot extract names, places, organizations	Use spaCy or BERT for extraction
No summarization	Cannot produce weekly briefings	Use a frontier LLM for the generation layer
7. Recommended Architecture
Jev handles the high-volume, low-latency classification layer. Every scraped post goes through Jev for sentiment, topic, LGA relevance, intensity, and opposition signal.

A frontier LLM handles the low-volume, high-value generation layer. Weekly briefing drafts, narrative summaries, and recommended actions are generated by an LLM using Jev's structured outputs as input.

Traditional ML handles aggregation and prediction. Random Forest or Logistic Regression on Jev labels produces LGA risk classifications. Pandas handles all counting and grouping.

The dashboard handles delivery. Looker Studio (or Panel / Datawrapper / GitHub Pages) presents the aggregated outputs to the campaign team.

8. Final Deliverables
Deliverable 1: Classified Post Corpus
A daily-updated table containing every scraped post with Jev-assigned labels, probabilities, confidence scores, and routing decisions. Foundation for all other outputs.

Deliverable 2: Bauchi LGA Sentiment Heatmap
An interactive map of all 20 LGAs coloured by sentiment intensity. Click-through reveals top three topics driving sentiment and 7-day/30-day trends.

Deliverable 3: Opposition Comparison Dashboard
Side-by-side sentiment metrics for the APM candidate, the PDP candidate, and the APC candidate. Includes mention volume, positive/negative ratio, average confidence, and top topics per candidate.

Deliverable 4: LGA Risk Prediction Report
Weekly classification of each LGA as safe, swing, or at-risk. Each classification includes model version, confidence level, and the top three signals driving the classification.

Deliverable 5: Daily Briefing Template
One-page template filled in 15 minutes each morning: top three LGAs by negative sentiment change, top three emerging topics, one opposition narrative gaining traction, one recommended action.

Deliverable 6: Agent Operations Manual
Question schema with version history, confidence routing protocol, escalation procedure for low-confidence decisions, weekly evaluation cycle instructions, and the "What Jev Cannot Do" limitations section.

9. Key Takeaways for Agents
Start with the question schema, not the scraping. If the questions are wrong, the classification data is useless regardless of how much text is collected. Spend the first week defining and stress-testing questions against a small sample of manually labelled posts before building full scrapers.

Build the confidence routing before building the dashboard. The routing rule determines what data reaches the dashboard. Define what percentage of posts falls below the threshold and adjust based on weekly evaluation results.

The LG election results are the baseline, not the prediction target. A model that says "Bauchi LGA is safe" when the APM won it with 125,170 votes is restating the obvious. Focus on detecting changes from that baseline, especially in narrow-margin LGAs.

Train the human reviewers first. Human reviewers are the quality gate. They must understand the question schema intimately, articulate why a Jev decision was wrong, and document reasoning in a format that feeds back into schema improvement.

The demo is a single insight, not a dashboard tour. Lead with one actionable finding: "In Ningi LGA, negative sentiment around 'youth unemployment' has risen 40% in the last two weeks. The APC is gaining traction on this topic. We recommend a targeted town hall in Ningi within 14 days." Then show the dashboard as the tool that produced that insight.

Document the limitations before the campaign asks. A dashboard that silently fails on long threads or miscounts mentions is worse than no dashboard at all.

Start with Looker Studio, scale to Panel or GitHub Pages. Get a working dashboard in front of the campaign team this week. Migrate to more powerful options as needs grow.

The framework is a loop. Build it, evaluate it weekly, improve it iteratively. The first version will be imperfect. The tenth version will be a genuine competitive advantage.

10. Ethical and Legal Notes
Scrape only public data. Nairaland posts, news articles, and public Facebook pages are fair game. Never scrape private groups or DMs.

Anonymize usernames. Store sentiment and topic data, not identifiable user profiles.

Respect robots.txt and rate limits. Add delays between requests.

Be transparent. If the campaign uses this data publicly, disclose that it is based on public social media and news analysis, not private polling.

Version and log everything. Every output must be traceable to the schema, model, and data that produced it.

11. Quick-Start Checklist for Agents
□ Register for a TypeSafe API key
□ Define and version the Jev question schema
□ Build scrapers for Nairaland, three news sites, and three public Facebook pages
□ Set up GitHub Actions for daily scraping
□ Run a small pilot classification on 500 manually-labelled posts
□ Build the confidence routing logic
□ Aggregate pilot data by LGA and date
□ Create the Google Sheet with the standardized column structure
□ Build the Looker Studio dashboard connected to the Sheet
□ Share the dashboard link with the campaign team
□ Run the first weekly evaluation cycle (100 sampled posts, human-labelled)
□ Document the first "What Jev Cannot Do" findings
□ Deliver the first daily briefing template
□ Schedule the weekly evaluation and schema review meeting
End of Document — Version 1.0