# Memory Tracking Improvements

## Problem

The original `PerformanceTracker` used Python's `tracemalloc` module, which only tracks memory allocated through Python's memory allocator. This misses:

- **C++ allocations** from USD library (Pixar's core USD implementation)
- **C++ allocations** from the custom Parquet plugin
- **Arrow/Parquet** library allocations
- **Any other native library** allocations

Since the majority of work happens in C++ (USD stage operations, Parquet file I/O), the memory tracking was essentially useless for benchmarking.

## Solution

Replaced `tracemalloc` with **process-level memory tracking** using `psutil`:

### What Changed

1. **Added `psutil` dependency** to `pyproject.toml`
   - `psutil` provides cross-platform access to process memory metrics
   
2. **Updated `PerformanceTracker` class** in `tests/benchmarks/results.py`
   - Now tracks **RSS (Resident Set Size)** - the actual physical memory used by the process
   - Captures **all allocations** (Python + C++ + everything else)
   - Reports memory **delta** from baseline (memory used during the benchmark)

### How It Works

```python
with PerformanceTracker() as tracker:
    # Baseline memory recorded on entry
    stage = Usd.Stage.Open("scene.usda")  # C++ allocations
    # ...benchmark operations...
    # Peak and current memory recorded on exit

# tracker.result contains:
#   - current_bytes: memory delta at exit
#   - peak_bytes: maximum memory delta during context
```

### Memory Metrics

- **RSS (Resident Set Size)**: Physical memory actually in RAM
- **Baseline**: Process memory before the benchmark operation
- **Delta**: Additional memory used during the operation
- **Peak**: Maximum memory reached during the operation

### Fallback Support

The implementation includes fallback for systems without `psutil`:
- **Unix/macOS**: Uses `resource.getrusage()` (built-in)
- **No modules**: Returns 0 (graceful degradation)

## Verification

Test the memory tracker:

```bash
uv run python -c "
import sys
sys.path.insert(0, 'tests/benchmarks')
from results import PerformanceTracker

with PerformanceTracker() as tracker:
    data = [0] * 1_000_000  # ~8MB allocation
    
print(f'Memory used: {tracker.result.peak_bytes / (1024*1024):.2f} MB')
"
```

## Impact on Benchmarks

All benchmark tests using `PerformanceTracker` now accurately measure:
- ✅ Memory used when loading Parquet sublayers
- ✅ Memory used by USD stage composition
- ✅ Memory used by Parquet plugin cache
- ✅ Memory differences between USDC and Parquet formats

This provides meaningful data for comparing the memory efficiency of different formats and configurations.
