"""
SpendSense - Dashboard Builder
================================
Embeds results.json and benchmark.json into dashboard_template.html
to produce a single, self-contained dashboard.html.

Usage:
    python3 generate_data.py
    python3 pipeline.py
    python3 benchmark.py
    python3 build_dashboard.py
    open dashboard.html
"""

import json

with open("dashboard_template.html") as f:
    html = f.read()

with open("results.json") as f:
    results = json.load(f)

with open("benchmark.json") as f:
    benchmark = json.load(f)

html = html.replace("__RESULTS_JSON__",   json.dumps(results))
html = html.replace("__BENCHMARK_JSON__", json.dumps(benchmark))

with open("dashboard.html", "w") as f:
    f.write(html)

print(f"Built dashboard.html ({len(html):,} bytes)")
