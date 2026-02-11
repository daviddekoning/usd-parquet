# Changes to `tests/benchmarks/test_single_property.py`

## Overview
Updated `test_single_property_cold` to use the `PerformanceTracker` probe system for detailed performance analysis.

## Key Changes
- **Detailed Probes**: Now measures timing and memory at 4 stages:
  1. `start`: Baseline.
  2. `base_layer_loaded`: After loading the base scene.
  3. `sublayer_composition`: After composing the property sublayer.
  4. `property_read`: After reading a single property value.
- **Data Collection**: Captures full probe data for all 5 runs.
- **Reporting**: Stores detailed probe data in `BenchmarkResult.extra["detailed_probes"]`, enabling the generation of detailed charts in the HTML report.
- **Methodology**: Changed from a simple `BenchmarkTimer` wrapper to an explicit loop with `PerformanceTracker` context manager, similar to `test_initial_load`.
