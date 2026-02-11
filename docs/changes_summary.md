# Changes Summary

## 1. Test Update: `tests/benchmarks/test_initial_load.py`
- **Probe Points**: Updated to measure 4 key stages:
  1. `start` (baseline)
  2. `base_layer_loaded`
  3. `sublayer_added`
  4. `composition_complete`
- **Data Collection**: Now captures detailed probe data from ALL runs (not just the last one) into `all_probe_data`.
- **Result Storage**: Stores `detailed_probes` in the `extra` field of `BenchmarkResult` for report generation.

## 2. Report Generation Update: `tests/benchmarks/report.py`
- **New Charts**: Added logic to generate detailed Timing and Memory charts for tests that provide probe data.
- **Visuals**:
  - **Timing Chart**: 
    - Line: Cumulative time (elapsed_since_start)
    - Bars: Time per step (elapsed_since_last)
  - **Memory Chart**:
    - Line: Cumulative memory (delta_since_start)
    - Bars: Memory per step (delta_since_last)
- **Aggregation**: Automatically calculates the average across all runs for each format to produce smooth trend lines.
- **Comparison**: Plots all formats (usdc, parquet variants) on the same chart for easy comparison.
- **Drawing Order**: Ensures Line charts are drawn on top of Bar charts for visibility.
