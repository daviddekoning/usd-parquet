# Configuration Update: ZSTD Only

## Changes
- **Data Generation**: Updated `tests/benchmarks/generate_test_data.py` to only generate `ZSTD` compressed Parquet files.
- **Test Configuration**: Updated `tests/benchmarks/conftest.py` to only test `ZSTD` and `USDC` formats, preventing "Skipped" results for the removed formats.

## Cleanup Command
You can run the following command to remove the now-obsolete `none` and `snappy` compressed files:

```bash
find tests/data/benchmarks -type f \( -name "properties_none_*.parquet" -o -name "properties_snappy_*.parquet" \) -delete
```
