# SpendSense

**Intelligent, real-time spend insights for individuals — not just another dashboard.**

Built for **Gen AI Academy APAC 2026 — Cohort 2** (Hack2Skill × Google Cloud × NVIDIA), Hackathon Prototype Submission track: *Data Analytics, Visualization & Decision-Support*.

Team: **DataPilot** — see [Team](#Leader:Paulami_Bhosle)

---

## 1. The Problem

Most people never look closely at their own transaction data until something goes wrong — an overspend, a duplicate charge, an unexplained large debit. Bank/UPI apps show raw transaction lists, but nobody has time to manually scan hundreds of rows a month to:

- spot **which transactions are unusual** for them, specifically (not just "large" in absolute terms),
- know **where their spend is trending** category by category, and
- get a **forward-looking number** ("you're on track to spend ₹X next month") instead of only a backward-looking statement.

**Real user**: anyone managing a personal or household budget — students, young professionals, or small shared households tracking monthly spend.

**Decision it supports**: *"Should I cut spending this month, and where exactly?"* — backed by flagged anomalies, a category breakdown, and a next-month forecast, instead of a gut feeling.

The cohort brief explicitly asks for *"moving from static dashboards to real-time, intelligent insights."* SpendSense's headline feature is exactly that: it doesn't just chart the data, it **writes a plain-English summary of what the data means** for the user, on top of the dashboard.

---

## 2. Pipeline (Ingest → Clean → Analyze → Model → Insight → Output)

| Stage | What happens | File |
|---|---|---|
| **Ingest** | Read a transactions CSV (bank/UPI export). In production: object dropped in **Cloud Storage**. | `generate_data.py` (synthetic data stand-in) |
| **Clean** | Dedupe, drop nulls, type-fix amounts/dates, normalize categories. In production: a **BigQuery** SQL/dbt cleaning step. | `pipeline.py :: load_and_clean()` |
| **Analyze** | Per-category monthly aggregation, total spend. | `pipeline.py :: category_breakdown()` |
| **Model** | Per-category z-score anomaly detection (log-transformed, robust to right-skew) + linear-trend forecast for next month's total spend. | `pipeline.py :: detect_anomalies()`, `forecast_next_month()` |
| **Insight** | Plain-English narrative generated from the aggregated stats (templated in the prototype; designed as a drop-in slot for a **Gemini** call — see below). | `pipeline.py :: build_insight_text()` |
| **Output** | `results.json` → rendered into `dashboard.html` (charts, anomaly table, forecast, narrative). | `dashboard.html` |

Run it yourself:

```bash
pip install -r requirements.txt
python3 generate_data.py      # generates transactions.csv (600K synthetic rows)
python3 pipeline.py           # runs the pipeline, writes results.json (uses GEMINI_API_KEY from env if present)
python3 build_dashboard.py    # embeds results.json into dashboard.html
open dashboard.html           # or just double-click it
```
## 3. Google Cloud Mapping

This prototype runs locally so it can be judged without cloud credentials, but it is architected 1:1 onto Google Cloud's data + application layer:

- **Cloud Storage** — raw transaction CSVs land here as the ingest point.
- **BigQuery** — the clean/aggregate/anomaly-scoring SQL would run here at production scale (the `pipeline.py` logic mirrors what a BigQuery scheduled query + scheduled stored procedure would do).
- **Looker / Looker Studio** — `dashboard.html` is a stand-in for a Looker dashboard; the same `results.json` schema maps directly onto Looker data sources/fields.
- **Gemini Enterprise Agent Platform** — the `build_insight_text()` function is intentionally isolated so its body can be swapped for a real Gemini API call (prompt: pass `category_breakdown`, `monthly_trend`, and `top_anomalies` as context, ask for a 2–3 sentence plain-English summary + one actionable recommendation). This is the "real-time intelligent insight" layer the cohort brief calls for, not just a static chart.

*(2+ Google Cloud services used: Cloud Storage + BigQuery + Looker, satisfying the requirement.)*

---

## 4. NVIDIA Acceleration

The pipeline is written in plain pandas so it runs anywhere — but it is **zero-code-change compatible with `cudf.pandas`**, NVIDIA RAPIDS' GPU accelerator for pandas.

- **CPU baseline (this repo, as submitted)**: `benchmark.py` runs the full pipeline at 10K / 100K / 600K rows. Measured locally:

  | Rows | Pipeline time (pandas / CPU) |
  |---|---|
  | 10,000 | 0.033 s |
  | 100,000 | 0.171 s |
  | 600,000 | 1.101 s |

- **GPU run**: open `notebooks/gpu_benchmark.ipynb` on a Colab GPU runtime (or any NVIDIA-GPU machine with RAPIDS installed) and run:

  ```bash
  pip install cudf-cu12 --extra-index-url=https://pypi.nvidia.com
  python3 -m cudf.pandas benchmark.py
  ```

  This re-runs the **identical script**, unmodified, on the GPU via `cudf.pandas`. Drop the resulting `benchmark.json` next to the CPU one and the numbers compare directly — that's the acceleration evidence for judging.

*(Satisfies the NVIDIA layer requirement via `cudf.pandas`; architecture also scales cleanly to RAPIDS Accelerator for Apache Spark / GKE if the dataset grows beyond a single-node workload.)*

---

## 5. What's in this repo

```
spendsense/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← GitHub Actions CI/CD (auto-deploys to Pages)
├── generate_data.py            ← synthetic transaction generator
├── pipeline.py                 ← clean → anomaly → forecast → Gemini insight
├── benchmark.py                ← CPU vs GPU timing benchmark
├── build_dashboard.py          ← embeds JSON into dashboard HTML
├── dashboard_template.html     ← dashboard shell (Chart.js, dark UI)
├── dashboard.html              ← FINAL demo file (auto-generated by CI)
├── results.json                ← latest pipeline output
├── benchmark.json              ← latest benchmark output
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 6. Gemini AI Live Insights

SpendSense now has a **zero-dependency live Gemini API integration** built directly into `pipeline.py`.

<img width="750" height="350" alt="image" src="https://github.com/user-attachments/assets/b53beda6-9bc9-46b8-b798-862cf427f4d2" />

It automatically scans for a `GEMINI_API_KEY` environment variable (either from your system environment, a local `.env` file, or GitHub Secrets).
- **If the API key is present**: It queries `gemini-2.5-flash` to construct a dynamic, personalized spending narrative and custom recommendation. The dashboard displays a glowing **[AI Powered]** badge.
- **If no API key is set**: It gracefully falls back to the deterministic rule-based template engine and displays a **[Rule Fallback]** badge, allowing local judges to run the pipeline out-of-the-box.

To set up the API key locally:
1. Create a `.env` file inside the `spendsense/` directory:
   ```env
   GEMINI_API_KEY=AIzaSy...your_gemini_key...
   ```
2. Re-run `python pipeline.py && python build_dashboard.py`.

---

## 7. Team

<img width="90" height="79" alt="image" src="https://github.com/user-attachments/assets/2a55b3f5-efd0-4432-9f59-bc86923dc9fb" />

**DataPilot** .                         

DataPilot is an agile squad in the Google Cloud Gen AI Academy APAC Edition. We leverage GCP and Gen AI to turn chaotic financial logs into predictive intelligence, redefining how organizations track, forecast, and protect their capital.

**Memebers**
Leader: Paulami Bhosle
Swapnil Adlinge
Nandha Kumar
Manish Lawaniya

---
## 8. Acknowledgements

Built for the Gen AI Academy APAC 2026, Cohort 2 hackathon (Hack2Skill, Google Cloud, NVIDIA).

---
