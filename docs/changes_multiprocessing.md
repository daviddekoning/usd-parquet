# Changes to Benchmark Tests

## Overview
Implemented process isolation for benchmark runs to ensure accurate memory measurements and eliminate cross-test contamination.

## Key Changes
- **Multiprocessing**: `test_initial_load.py` and `test_single_property.py` now run each iteration in a separate `multiprocessing.Process`.
- **Memory Isolation**: Each run starts with a fresh Python interpreter and USD library state.
- **Helper Functions**: Extracted test logic into standalone functions `_run_single_iteration` and `_run_single_property_iteration` to facilitate multiprocessing.
- **Queue-based Communication**: Uses `multiprocessing.Queue` to return detailed `ProbeResult` data from child processes to the main test runner.

## Benefits
- **Consistent Baselines**: Memory usage no longer decreases or drifts over multiple runs due to GC or caching behavior in the main process.
- **Accurate Profiling**: `MemoryTracker` now measures the true cost of operations from a clean slate every time.
