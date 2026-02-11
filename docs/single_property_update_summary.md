# Single Property Benchmark Update

## Changes
1. **Removed Warm Test**: Removed the separate `test_single_property_warm` test case.
2. **Enhanced Cold Test**: Updated `test_single_property_cold` to include a 50x repeat read loop within the same measurement session.
3. **Multiprocessing**: Used process isolation for each iteration.
4. **Filtering**: Updated `run_benchmarks.py` to support `--filter` argument.

## Results (10,000 prims, deep hierarchy)
- **Command**: `python3 tests/benchmarks/run_benchmarks.py ... --filter "single_property_cold"`
- **Report**: `tests/data/benchmarks/10000_deep/benchmark_report.html`

## Observations from New Test Structure
The new `test_single_property_cold` now captures 4 probe points per run:
1. `start`
2. `base_layer_loaded`
3. `sublayer_composition`
4. `property_read` (Initial cold read)
5. `property_read_warm_50x` (Subsequent 50 reads)

This allows direct comparison of cold vs warm access costs within the same context.
