# Benchmark Run Summary: 10,000 Prims, Deep Hierarchy

## Execution Details
- **Date**: 2026-02-10
- **Scale**: 10,000 prims
- **Hierarchy**: Deep
- **Command**: `python3 tests/benchmarks/run_benchmarks.py --scales 10000 --hierarchies deep`

## Results
- **Report Location**: `tests/data/benchmarks/10000_deep/benchmark_report.html`
- **JSON Data**: `tests/data/benchmarks/10000_deep/benchmark_results.json`

## Key Observations
- **Initial Load**:
  - `parquet_none` and variants show significantly lower memory usage compared to `usdc` during the `sublayer_added` step.
  - `usdc` shows a large memory spike (delta ~300MB) during `sublayer_added`, while `parquet` variants show minimal delta (<1MB or negative/zero due to lazy loading).
  - Timing for `parquet` variants (~0.11s) is much faster than `usdc` (~0.56s).

## New Visualizations
The HTML report now includes detailed breakdown charts for `initial_load_cold`:
1. **Timing Analysis**: 
   - Cumulative time (Line) shows total progression.
   - Step time (Bar) highlights the most expensive operations.
2. **Memory Analysis**:
   - Cumulative memory (Line) tracks total RSS growth.
   - Step memory (Bar) identifies which operations allocate the most memory.

These charts clearly demonstrate the lazy-loading advantage of the Parquet format, where memory is not consumed until data is actually accessed, unlike USDC which seems to load more metadata upfront.
