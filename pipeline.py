"""
SpendSense - Core Analytics Pipeline
=====================================
INGEST -> CLEAN -> ANALYZE -> MODEL (anomaly + forecast) -> INSIGHT -> OUTPUT

Run on CPU (anywhere):
    python3 pipeline.py

Run GPU-accelerated (Colab / GCP VM with RAPIDS):
    python3 -m cudf.pandas pipeline.py
    # or in a notebook: %load_ext cudf.pandas  (before importing pandas)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

import numpy as np
import pandas as pd

# Load .env file if present
for env_path in [".env"]:
    if os.path.exists(env_path):
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
            break
        except Exception:
            pass

GPU_ACTIVE = "cudf.pandas" in sys.modules


def load_and_clean(path="transactions.csv"):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.drop_duplicates(subset="txn_id")
    df = df.dropna(subset=["amount", "category", "timestamp"])
    df = df[df["amount"] > 0]
    df["amount"]   = df["amount"].astype(float)
    df["category"] = df["category"].str.strip()
    df["month"]    = df["timestamp"].dt.to_period("M").astype(str)
    return df


def detect_anomalies(df, z_thresh=3.0):
    df          = df.copy()
    df["log_amount"] = np.log1p(df["amount"])
    stats       = df.groupby("category")["log_amount"].agg(["mean", "std"]).reset_index()
    stats.columns = ["category", "cat_mean", "cat_std"]
    df          = df.merge(stats, on="category", how="left")
    df["cat_std"]  = df["cat_std"].replace(0, 1)
    df["z_score"]  = (df["log_amount"] - df["cat_mean"]) / df["cat_std"]
    df["is_anomaly"] = df["z_score"].abs() >= z_thresh
    return df


def forecast_next_month(df):
    monthly = df.groupby("month")["amount"].sum().reset_index().sort_values("month").reset_index(drop=True)
    if len(monthly) < 2:
        return monthly, None
    x = np.arange(len(monthly))
    y = monthly["amount"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    forecast = float(slope * len(monthly) + intercept)
    return monthly, max(forecast, 0.0)


def category_breakdown(df):
    return (
        df.groupby("category")["amount"].sum()
          .sort_values(ascending=False)
          .round(2).to_dict()
    )


def call_gemini_api(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(url, data=data,
                                       headers={"Content-Type": "application/json"},
                                       method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Warning] Gemini API failed: {e}. Using rule-based fallback.", file=sys.stderr)
        return None


def build_insight_text(monthly, forecast, anomalies_df, breakdown):
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        anom_subset = anomalies_df[anomalies_df["is_anomaly"]]
        top_anom_str = ""
        if not anom_subset.empty:
            top_anom_str = anom_subset.sort_values("z_score", ascending=False).head(5)[
                ["timestamp", "merchant", "category", "amount"]].to_string(index=False)

        prompt = f"""You are SpendSense, an intelligent AI financial assistant.
Analyze the user's spending data and generate a highly personalized, natural-sounding monthly insight summary (2-3 sentences) followed by exactly one actionable, concrete recommendation.

Spending summary:
- Total Spend: ₹{sum(breakdown.values()):,.2f}
- By Category: {json.dumps(breakdown)}
- Monthly Trend: {json.dumps([{"month": r["month"], "amount": r["amount"]} for _, r in monthly.iterrows()])}
- Next Month Forecast: {f"₹{forecast:,.2f}" if forecast else "Not enough data"}
- Anomalies Flagged: {len(anom_subset)}
- Top anomalies:
{top_anom_str}

Rules:
1. Speak directly to the user ("You spent...", "We noticed...").
2. Focus on the most significant category or worrying anomalies.
3. Keep under 100 words total.
4. No technical terms (z-score, pipeline, dataframe). Keep it conversational.
5. One brief paragraph + one bullet recommendation. No Markdown headers.
"""
        print("Calling Gemini 2.5 Flash for live insights...")
        insight = call_gemini_api(prompt, api_key)
        if insight:
            return insight, "Gemini 2.5 Flash"

    # Rule-based fallback
    top_cat          = max(breakdown, key=breakdown.get)
    last_month_spend = float(monthly.iloc[-1]["amount"]) if len(monthly) else 0
    n_anomalies      = int(anomalies_df["is_anomaly"].sum())
    trend            = "rising" if forecast and forecast > last_month_spend else "falling"

    parts = [
        f"Your top spending category is {top_cat} at ₹{breakdown[top_cat]:,.0f} total over the period.",
        (f"Last month's total was ₹{last_month_spend:,.0f}; the trend looks {trend}, "
         f"with next month forecast at ₹{forecast:,.0f}.") if forecast else
        "Not enough months of data yet to forecast next month.",
        f"{n_anomalies} unusual transactions were flagged — worth a manual review.",
    ]
    text = " ".join(parts) + \
           "\n\n💡 Recommendation: Review your top anomalies to identify potential subscription leaks or unexpected double charges."
    return text, "Rule-based Engine"


def run_pipeline(path="transactions.csv"):
    timings = {}

    t0 = time.perf_counter()
    df = load_and_clean(path)
    timings["clean_seconds"] = round(time.perf_counter() - t0, 4)

    t0 = time.perf_counter()
    anomalies_df = detect_anomalies(df)
    timings["anomaly_detection_seconds"] = round(time.perf_counter() - t0, 4)

    t0 = time.perf_counter()
    monthly, forecast = forecast_next_month(df)
    timings["forecast_seconds"] = round(time.perf_counter() - t0, 4)

    timings["total_seconds"] = round(sum(timings.values()), 4)

    breakdown = category_breakdown(df)
    insight_text, insight_source = build_insight_text(monthly, forecast, anomalies_df, breakdown)

    top_anomalies = (
        anomalies_df[anomalies_df["is_anomaly"]]
        .sort_values("z_score", ascending=False)
        .head(15)[["txn_id", "timestamp", "merchant", "category", "amount", "z_score"]]
        .copy()
    )
    top_anomalies["timestamp"] = top_anomalies["timestamp"].astype(str)
    top_anomalies["z_score"]   = top_anomalies["z_score"].round(2)

    result = {
        "engine":               "cudf.pandas (GPU)" if GPU_ACTIVE else "pandas (CPU)",
        "row_count":            int(len(df)),
        "timings":              timings,
        "total_spend":          round(float(df["amount"].sum()), 2),
        "category_breakdown":   breakdown,
        "monthly_trend": [
            {"month": r["month"], "amount": round(float(r["amount"]), 2)}
            for _, r in monthly.iterrows()
        ],
        "forecast_next_month":  round(forecast, 2) if forecast else None,
        "anomaly_count":        int(anomalies_df["is_anomaly"].sum()),
        "top_anomalies":        top_anomalies.to_dict(orient="records"),
        "insight_text":         insight_text,
        "insight_source":       insight_source,
    }

    with open("results.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps({"engine": result["engine"], "rows": result["row_count"],
                       "timings": timings, "insight_source": insight_source}, indent=2))
    return result


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "transactions.csv"
    run_pipeline(path)
