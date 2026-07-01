"""
SpendSense - Acceleration Benchmark
=====================================
Runs the pipeline at 10K / 100K / 600K rows and records timings.

On CPU:      python3 benchmark.py
On GPU:      python3 -m cudf.pandas benchmark.py  (Colab GPU runtime / GCP VM with RAPIDS)
"""

import json
import sys
import time

from generate_data import generate
from pipeline import run_pipeline

GPU_ACTIVE = "cudf.pandas" in sys.modules
SCALES = [10_000, 100_000, 600_000]


def main():
    results = []
    for n in SCALES:
        path = f"bench_{n}.csv"
        generate(num_rows=n, out_path=path)

        t0   = time.perf_counter()
        out  = run_pipeline(path)
        wall = round(time.perf_counter() - t0, 4)

        results.append({
            "rows":               n,
            "engine":             out["engine"],
            "wall_clock_seconds": wall,
            "pipeline_timings":   out["timings"],
        })
        print(f"[{out['engine']}] {n:,} rows -> {wall}s")

    payload = {
        "engine":  "cudf.pandas (GPU)" if GPU_ACTIVE else "pandas (CPU)",
        "results": results,
    }
    with open("benchmark.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("\nWrote benchmark.json")


if __name__ == "__main__":
    main()
