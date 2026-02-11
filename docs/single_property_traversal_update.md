# Single Property Traversal Update

## Changes
1. **Multiprocessing**: `test_single_property_traversal` now runs each iteration in a separate process, ensuring clean memory.
2. **Probes**: Added 4 setup probes (`start`, `stage_loaded`, `paths_collected`) and ~10 progress probes during the traversal loop (`traversal_10pct`, `traversal_20pct`, etc.).
3. **Data Collection**: Detailed probe data is collected and passed to the results, allowing visualization of memory/time consumption during the traversal.

## Results
- **Command**: `python3 tests/benchmarks/run_benchmarks.py ... --filter "single_property_traversal"`
- **Report**: `tests/data/benchmarks/10000_deep/benchmark_report.html`

The charts will now show the cost of setup (loading stage, collecting paths) vs the actual cost of traversing and reading properties, and how memory usage evolves during the traversal.
