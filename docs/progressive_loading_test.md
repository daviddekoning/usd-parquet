# Progressive Loading Test

## Changes
- **Data Generation**: Updated `tests/benchmarks/generate_test_data.py` to use a Parquet row group size of **500 rows** (previously 10,000).
- **Data Regeneration**: Regenerated 10,000 prim dataset.
- **Benchmark Run**: Ran `single_property_traversal` to capture progressive loading behavior.

## Results
- **Report**: `tests/data/benchmarks/10000_deep/benchmark_report.html`

With 500-row groups, the memory profile during traversal should show a "staircase" pattern for Parquet formats, as data is loaded in chunks of 500 rows, rather than all at once or in very large chunks.
