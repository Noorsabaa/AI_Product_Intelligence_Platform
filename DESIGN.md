# Product and pipeline decisions

## The problem this version addresses

The earlier product blurred several different jobs: comparing sample applications, assigning predefined issue categories, generating engineering recommendations, and tracking actions. A support manager first needs to understand what customers are saying, how that is changing, and which evidence supports a concern. A named-app demonstration and a crowded action interface obscure that job.

This version organizes one company's feedback into a short sequence: sentiment → category trend → complaint priority → evidence → saved performance report. It describes reported experience. It does not claim to diagnose technical service performance from review text.

## Why this interface

The cream canvas, beige sidebar and paper-colored panels make the page read like an analysis report. Brown is reserved for emphasis and negative-review trends; positive/neutral cues use restrained blue and taupe. The design avoids a wall of competing colored cards. Serif headings establish report hierarchy, while plain sans-serif labels and tabular numbers support scanning.

Each sidebar item opens its own page: Dashboard, Trends, Priorities, Generate report, Report history and Data. Dashboard contains the four KPIs and a short period summary, with Export above them. Trends contains the line chart and category selector; Priorities contains the evidence ranking; Generate report contains only the creation form, while Report history is a separate archive belonging to the signed-in account. Import/analysis controls live under Data. Initial priorities are limited to eight rows with explicit expansion. Detailed evidence and score explanations open only when requested. The chart code loads only when Trends opens.

Counts and share are separate chart modes: counts reveal workload, while shares distinguish changing complaint mix from changing overall submission volume. Straight line segments avoid suggesting smoothed measurements that were never observed. Mobile tables scroll inside their own panel; navigation becomes a drawer. Color is supplemented with words and numbers.

## Why embeddings + UMAP + HDBSCAN

A fixed-label classifier can only choose among its supplied labels. That conflicts with the requirement to surface new issues. Sentence embeddings instead represent similar meaning, UMAP reduces dimensionality for density estimation, and HDBSCAN discovers dense groups without a requested category count. Class-based TF-IDF extracts phrases to describe each group.

This follows the broad BERTopic approach but is implemented as a small explicit pipeline rather than a second orchestration framework. [BERTopic's paper](https://arxiv.org/abs/2203.05794) describes embedding-based clusters with class-based TF-IDF representations. [Sentence Transformers documentation](https://sbert.net/docs/sentence_transformer/pretrained_models.html) covers semantic embeddings and the speed/quality tradeoffs of the MiniLM family. [Scikit-learn's HDBSCAN documentation](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html) explains density-based grouping and noise labels.

Crucially, there is **no outlier reassignment**. A review needs density membership and sufficient similarity to the group's centroid in the original embedding space. Unsupported language, short content, isolated novel issues and weak matches remain ungrouped. This is consistent with [BERTopic's discussion of outliers](https://maartengr.github.io/BERTopic/getting_started/outlier_reduction/outlier_reduction.html), although we deliberately do not apply its optional outlier-reduction steps.

“Not forced” does not mean “never misclassified.” Similarity thresholds are safeguards, not calibrated correctness probabilities. Novel wording may resemble an existing group and still be misclustered. Domain-labeled evaluation, review of representative and rejected items, and monitoring are required before claiming reliable production quality.

The supplied sample had 468 eligible distinct English texts. Local probes of raw embeddings, PCA and UMAP showed more interpretable recurring issue groups with UMAP. The final run produced 34 groups, but no labeled test set establishes that 34 is optimal. Thresholds and topic granularity are explicit implementation choices, not learned guarantees of the correct business taxonomy.

### Stability and naming

Exact normalized duplicates are encoded once and count once during clustering. They remain separate feedback records when their date/customer/source identity differs. This stops repeated templates from manufacturing apparent semantic density while preserving submission volume.

A one-to-one overlap match preserves an existing category ID and custom display name when at least half of the union of old/new review members overlaps. Substantial splits or merges can create new IDs. This is conservative continuity, not permanent taxonomy identity. Saved reports preserve historical membership and names independently, so reanalysis cannot rewrite past evidence.

Automatically extracted names can be awkward. Managers can edit display names without changing membership; extracted keywords remain visible. The app does not invent a service name, merge clusters on a manager's behalf, or pretend generated phrases match the company's architecture.

### Alternative when models are unavailable

TF-IDF + truncated SVD + HDBSCAN is implemented as lexical mode. It has no neural-model download and still discovers categories, but it separates paraphrases more easily and relies on ratings for sentiment. NMF is another defensible lexical topic model, but generally requires choosing a topic count and produces mixture weights that still need an abstention policy; see [scikit-learn's topic-extraction example](https://scikit-learn.org/stable/auto_examples/applications/plot_topics_extraction_with_nmf_lda.html). Density clustering is the closer match to this user's unknown-category requirement.

## Sentiment is separate from topic discovery

English text sentiment uses a local RoBERTa classifier. It was trained outside this company's support domain, so its labels are predictions. Other languages use supplied ratings; unrated unsupported text stays unavailable. The interface discloses those method counts and each evidence item identifies its method. Missing ratings never become neutral results.

Topics are discovered across all sentiments, allowing the same area to have both praise and complaints. Negative records drive complaint volume; neutral is separate. No Gemini call is needed for category assignment, priority arithmetic or report generation.

## Priority score: an inspectable triage heuristic

For a category, let `n` be negative feedback, `N` all negative feedback, `t` analyzed feedback in that category, and `p` the workspace negative fraction:

- **Volume, 0–45:** `45 × sqrt(n / N)`. Repeated complaints matter, while the square root prevents one large category from swallowing every other signal.
- **Concentration, 0–30:** `30 × (n + 5p) / (t + 5)`. Five observations of shrinkage toward the workspace rate limit tiny all-negative samples.
- **Growth, 0–25:** compare category-negative share of all analyzed feedback in the latest seven days with the previous 28 days. Reward a relative rise, capped at 200%. Require 35 days of observed history, at least 10 recent and 20 baseline records, and at least five recent category complaints. With a zero category baseline, five recent complaints receive the capped contribution; no infinite growth percentage is displayed.

The sum is rounded to a 0–100 ranking. High starts at 65 and Medium at 40. These weights and labels are product heuristics, not learned business severity or confidence. The UI exposes each component. The category's positive/neutral records supply its concentration denominator; other workspace records supply volume and growth denominators. The global CSV exposes the broader context.

Change vs baseline is a **percentage-point difference in category complaints divided by all analyzed feedback**, not a percentage change in raw complaints and not the adjacent period-wide share of negative reviews. Short history shows “Insufficient history.” Higher priority is not proof of a service incident.

## Reports describe the evidence

Reports are deterministic summaries built from the same snapshot as their tables. This eliminates numerical disagreement and unsupported engineering advice. They include sentiment, largest complaint areas, supported changes, supplied service/segment breakdowns, coverage and limitations.

Username/password accounts select an isolated workspace database on the server. Dashboard queries, report generation, history, direct report reads and exports all use that authenticated context; client-supplied user IDs cannot choose another workspace.

A report stores its period, generation time, analysis run, figures, category labels and all source review evidence in SQLite. It remains readable after replacement of the active dataset. The explicit raw customer identifier is omitted from stored report evidence and exports; review text itself can still contain personal data. Production retention/access policies remain necessary.

Customer segments and service areas are only compared when the importer supplies them. Complaint counts cannot establish which segment has the worst experience without segment population/exposure data. Likewise, a low-volume strategic account may be more important than hundreds of public reviews; this version does not fabricate account value or revenue weighting.

## Efficiency and operational boundaries

The existing cached-data rerun took approximately 30 seconds for 3,437 records. Neural work is batched; normalized embeddings and sentiment results are persisted by text hash and model name. CPU thread use is bounded. Unchanged text does not require another model prediction. Reports require no external API call.

Imports validate before writes. Analysis reserves a persisted single-run lock and publishes derived data atomically only on success; failed runs preserve the prior snapshot. Dashboard reads use a consistent database transaction. Reports are blocked when imported feedback has not been analyzed. Evidence requests detect a changed published run and ask the manager to refresh rather than attach a new result to an old score.

Local discovery fits at most 10,000 distinct eligible texts, selected deterministically, to bound memory. Excess texts are explicitly marked with `discovery_capacity_limit` and left ungrouped. This is a local scale limit, not an enterprise capacity claim. Dashboard aggregation and reports still load their scoped rows in memory; saved evidence increases storage with each report. Larger deployments need incremental processing, indexed aggregate tables, durable workers and retention controls.

## What the best production version would add next

1. Validate against a held-out, human-labeled sample from the actual company's support data. Measure topic purity/coverage, sentiment errors, emerging-issue recall and label stability, including rejected items.
2. Add multilingual embeddings and language-appropriate sentiment only after evaluation; split long or multi-issue feedback into traceable spans. Current English-only discovery is a significant limit for global SaaS companies.
3. Connect the company's actual support system and account metadata. Add account-aware deduplication, source IDs, service exposure denominators and optional business-impact weights that a manager can understand.
4. Extend the implemented local username/password accounts with production identity review, team roles, MFA/SSO, audit logs, encryption/retention policy, secure backups and a separate job queue before hosted multi-user use. Per-user local database isolation is implemented; enterprise deployment architecture is not.
5. Add reviewer-approved category merges/splits, representative-review checks, drift monitoring and report comparison across compatible snapshots. Persistent report archives already provide the necessary historical evidence.

The practical value for SaaS/B2B support is faster complaint triage and a defensible handover record. Its strongest claim is that managers can move from a trend or score to the customer statements behind it. It should not claim automated root-cause diagnosis, engineering planning or causal measurement of service reliability.

## Account design

The requested account boundary is a user, not a shared organization. Every user receives a generated internal ID and a separate SQLite workspace. A pure ASGI middleware keeps that context through background analysis, following the context-propagation considerations in [Starlette's middleware documentation](https://www.starlette.io/middleware/). Report IDs are random, but authorization does not depend on their secrecy: an ID from another account is absent from the current user's database.

Passwords are salted and hashed with scrypt (`N=2^17, r=8, p=1`), matching an [OWASP documented configuration](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Session tokens are random, stored as hashes, expire after seven days and are revoked on logout. Mutating API calls require a session CSRF token and reject mismatched browser origins. Signup and login attempts are rate limited in persistent storage.

No email address, SMTP integration or outbound account email is used, as requested. The app does not provide password recovery, account sharing or production concurrency management. Tests verify separate-account dashboards, report lists, direct report URLs, exports, session expiry and logout. These checks are useful evidence, not a substitute for a production security review.
