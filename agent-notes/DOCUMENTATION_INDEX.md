# Documentation Index

This session created comprehensive documentation for the USD Parquet plugin benchmark suite.

## Quick Reference

**Want benchmark results?** → Start with `BENCHMARK_SUMMARY_VISUAL.txt` or `COMPLETE_BENCHMARK_RESULTS.md`

**Want to run benchmarks?** → See `run_benchmarks.sh` and environment setup in `README.md`

**Want to understand the fixes?** → See `SESSION_SUMMARY.md`

---

## Documentation Files

### Benchmark Results
1. **`BENCHMARK_SUMMARY_VISUAL.txt`** - Quick visual summary with charts
2. **`COMPLETE_BENCHMARK_RESULTS.md`** - Detailed analysis of all 8 test cases
3. **`BENCHMARK_RESULTS_INITIAL_LOAD.md`** - Deep dive on initial load test
4. **`tests/data/benchmarks/10000_flat/benchmark_results.json`** - Raw JSON data

### Implementation Changes
5. **`SESSION_SUMMARY.md`** - Complete session overview (START HERE)
6. **`MEMORY_TRACKING_FIX.md`** - Memory tracking improvements explained
7. **`MEMORY_TRACKING_CHANGES.md`** - Technical details of memory fix
8. **`TEST_DATA_GENERATION_IMPROVEMENTS.md`** - Test data optimization
9. **`CHANGES_SUMMARY.md`** - Quick reference of all changes

### Usage Guides
10. **`tests/data/benchmarks/README.md`** - Test data directory structure
11. **`run_benchmarks.sh`** - Executable script for running benchmarks
12. **`demo_memory_tracking.py`** - Memory tracker demonstration

---

## File Descriptions

### `BENCHMARK_SUMMARY_VISUAL.txt`
Visual bar chart summary of key metrics. **Best for quick overview**.

Example:
```
INITIAL LOAD (Lower is better)
---------------------------------
Parquet (all):     47 ms   █  18x FASTER ✓
USDC:             856 ms   ████████████████████  baseline
```

### `COMPLETE_BENCHMARK_RESULTS.md`
Comprehensive analysis with:
- All 8 test cases explained
- Performance comparisons
- Use case recommendations
- Trade-off analysis

### `SESSION_SUMMARY.md`
Complete overview of this session:
- What was fixed (memory tracking, test generation)
- Benchmark results summary
- Files modified
- Next steps

### `MEMORY_TRACKING_FIX.md`
Technical explanation of:
- Why `tracemalloc` was wrong
- How `psutil` fixes it
- Implementation details
- Before/after comparison

### `TEST_DATA_GENERATION_IMPROVEMENTS.md`
Optimization details:
- File existence checking
- `--force` flag usage
- Performance improvements (27,000x speedup)
- Usage examples

---

## Quick Start Guide

### 1. Review Results
```bash
# Visual summary
cat BENCHMARK_SUMMARY_VISUAL.txt

# Detailed analysis
cat COMPLETE_BENCHMARK_RESULTS.md
```

### 2. Run Benchmarks
```bash
# Set environment
export PXR_PLUGINPATH_NAME=$(pwd)/build/resources
export PYTHONPATH=~/OpenUSD-25.11-install/lib/python

# Run all tests
./run_benchmarks.sh --benchmark-scale 10000 --benchmark-hierarchy flat -v
```

### 3. Generate Test Data
```bash
# Generate (skips existing files)
uv run python tests/benchmarks/generate_test_data.py --scale 10000 --hierarchy flat

# Force regeneration
uv run python tests/benchmarks/generate_test_data.py --scale 10000 --hierarchy flat --force
```

---

## Key Findings Summary

### Parquet Performance
- ⚡ **18x faster** initial load (46ms vs 856ms)
- 💾 **55% smaller** files (1.47 MB vs 3.28 MB with zstd)
- ✅ True lazy loading (zero memory on open)
- 🎯 Best for: Large scenes, sparse access, distribution

### USDC Performance
- ⚡ **2.2x faster** traversals (38ms vs 83ms)
- ⚡ **2.1x faster** multi-property reads (222ms vs 467ms)
- ✅ Consistent, predictable performance
- 🎯 Best for: Bulk reads, complete traversals, maximum throughput

### The Trade-Off
**Parquet**: Fast to open, slower to read everything  
**USDC**: Slow to open, fast to read everything

---

## Files Modified

### Core Implementation
- `tests/benchmarks/results.py` - Memory tracking rewrite
- `tests/benchmarks/generate_test_data.py` - Smart file generation
- `pyproject.toml` - Added psutil dependency

### New Utilities
- `run_benchmarks.sh` - Benchmark runner
- `demo_memory_tracking.py` - Memory demo

### Documentation (12 files)
All files listed above in "Documentation Files" section

---

## Benchmark Test Cases

1. **File Size** - Storage efficiency comparison
2. **Initial Load** - Sublayer composition time
3. **Single Property (Cold)** - First access performance
4. **Single Property (Warm)** - Cache performance
5. **Single Property Traversal** - Read one property from all prims
6. **Multiple Property Retrieval** - Read 6 properties from one prim
7. **Multiple Property Traversal** - Read 6 properties from all prims
8. **Random Access** - Worst-case cache behavior

Total: **33 individual tests** (4 formats × 8 test cases + file size)

---

## Environment Requirements

- OpenUSD v25.11+
- Apache Arrow C++
- Python 3.12+
- psutil (for memory tracking)
- Built plugin: `build/libparquetFormat.dylib`

---

## Next Steps

### Additional Testing
- [ ] Test with 100K and 1M prim scales
- [ ] Test deep hierarchy (not just flat)
- [ ] Test different Parquet row group sizes
- [ ] Add HTML report generation
- [ ] Add continuous memory polling

### Analysis
- [ ] Visualize results with charts
- [ ] Compare memory usage at different scales
- [ ] Profile cache hit rates
- [ ] Analyze compression trade-offs

---

## Contact & Context

This documentation was created during a benchmark testing session on 2026-02-10.

The USD Parquet plugin is a proof-of-concept custom file format for OpenUSD that uses Apache Parquet for property storage with lazy loading capabilities.

See `README.md` and `architecture.md` for project background.
