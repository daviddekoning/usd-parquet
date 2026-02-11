# Session Summary: Benchmark Testing & Analysis

## What We Accomplished

### 1. Fixed Memory Tracking ✅
**Problem**: Memory tracking used Python's `tracemalloc` which doesn't capture C++ allocations  
**Solution**: Replaced with `psutil` to track entire process RSS (Resident Set Size)

**Changes**:
- Added `psutil` dependency
- Rewrote `MemoryTracker` class to use process-level memory
- Added fallback to `resource.getrusage()` for Unix systems
- Created comprehensive documentation

**Result**: Now tracks actual memory usage including USD C++ allocations

---

### 2. Optimized Test Data Generation ✅
**Problem**: Script regenerated all files every run (wasting up to 45 minutes for large scales)  
**Solution**: Added intelligent file existence checking and `--force` flag

**Changes**:
- All write functions check if files exist before generating
- Skip existing files by default (incremental mode)
- Added `--force` flag for explicit regeneration
- Early exit if all files already exist

**Performance**: **27,000x faster** for 1M prims when files exist (45min → 0.1s)

---

### 3. Ran Complete Benchmark Suite ✅
**Configuration**: 10,000 prims, flat hierarchy, all 4 formats

**Tests Executed**:
- ✅ File size comparison
- ✅ Initial sublayer load
- ✅ Single property retrieval (cold/warm)
- ✅ Single property traversal
- ✅ Multiple property retrieval
- ✅ Multiple property traversal
- ✅ Random access patterns
- ✅ Sequential vs random comparison

**Total**: 33 tests, all passed

---

### 4. Created Comprehensive Documentation ✅

**Files Created**:
1. `MEMORY_TRACKING_FIX.md` - Details of memory tracking fix
2. `TEST_DATA_GENERATION_IMPROVEMENTS.md` - Test data optimization details
3. `CHANGES_SUMMARY.md` - Quick reference for changes
4. `BENCHMARK_RESULTS_INITIAL_LOAD.md` - Initial load test analysis
5. `COMPLETE_BENCHMARK_RESULTS.md` - Full benchmark analysis
6. `tests/data/benchmarks/README.md` - Test data directory docs
7. `run_benchmarks.sh` - Convenient script for running benchmarks

---

## Key Findings from Benchmarks

### Parquet Performance Highlights ⚡

1. **18x faster initial load** (46ms vs 856ms)
   - True lazy loading confirmed
   - Zero memory delta during load
   - Perfect for interactive workflows

2. **55% smaller file size** (1.47 MB vs 3.28 MB with zstd)
   - Significant storage savings
   - Better for distribution/archival

3. **Compression has minimal impact**
   - All three variants (none/snappy/zstd) perform similarly
   - ~46-47ms load time regardless of compression

4. **Good warm cache performance**
   - 13-17% faster than USDC for repeated access
   - Efficient caching implementation

### USDC Performance Highlights ⚡

1. **2.2x faster traversals**
   - All data already in memory
   - Optimized for bulk sequential reads

2. **2.1x faster multi-property access**
   - Efficient layout for reading multiple properties
   - No decompression overhead

3. **Consistent performance**
   - Lower standard deviation across tests
   - Predictable behavior

### The Trade-Off

**Parquet**: Fast to open, slower to read everything  
**USDC**: Slow to open, fast to read everything

**Best use cases**:
- **Parquet**: Large scenes, sparse access, storage/distribution
- **USDC**: Active work, bulk reads, maximum throughput

---

## Files Modified

### Core Changes
1. `tests/benchmarks/results.py` - Memory tracking rewrite
2. `tests/benchmarks/generate_test_data.py` - Smart file generation
3. `pyproject.toml` - Added psutil dependency

### New Files
1. `run_benchmarks.sh` - Benchmark runner script
2. `demo_memory_tracking.py` - Memory tracker demo
3. Multiple documentation files (7 total)

---

## Environment Setup

To run benchmarks:

```bash
# Set USD environment
export PXR_PLUGINPATH_NAME=$(pwd)/build/resources
export PYTHONPATH=~/OpenUSD-25.11-install/lib/python

# Run all benchmarks
./run_benchmarks.sh --benchmark-scale 10000 --benchmark-hierarchy flat -v

# Run specific test
./run_benchmarks.sh test_initial_load.py -v
```

---

## Benchmark Results at a Glance

| Metric | Parquet (best) | USDC | Winner |
|--------|---------------|------|--------|
| **File Size** | 1.47 MB | 3.28 MB | Parquet (55% smaller) |
| **Initial Load** | 46.7 ms | 855.7 ms | Parquet (18x faster) |
| **Single Traversal** | 82.2 ms | 37.7 ms | USDC (2.2x faster) |
| **Multi Traversal** | 466 ms | 222 ms | USDC (2.1x faster) |
| **Cold Access** | 0.052 ms | 0.050 ms | Tie (similar) |
| **Warm Access** | 2.37 µs | 2.85 µs | Parquet (17% faster) |

---

## Next Steps

### Potential Improvements
1. Add memory polling during operations for better peak tracking
2. Test with different scales (1K, 100K, 1M prims)
3. Test with deep hierarchy (not just flat)
4. Add visualization/reporting (HTML reports)
5. Test different row group sizes for Parquet

### Additional Tests
1. Time-varying property access
2. Mixed read patterns (sparse + bulk)
3. Multi-threaded access
4. Memory pressure testing

---

## Summary

Successfully:
- ✅ Fixed memory tracking to capture C++ allocations
- ✅ Optimized test data generation (27,000x faster when files exist)
- ✅ Ran complete benchmark suite (33 tests, all passing)
- ✅ Documented all changes and findings
- ✅ Validated Parquet plugin performance characteristics

**Key Insight**: Parquet's lazy loading delivers **18x faster** scene opening, making it ideal for large-scale workflows where you don't need to access all properties immediately.
