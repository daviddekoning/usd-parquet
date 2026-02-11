# PerformanceTracker Enhancement

## Overview

The `PerformanceTracker` class has been enhanced to be a general-purpose performance measurement tool that tracks both **timing** and **memory usage** throughout a test, with support for intermediate measurement points called **probes**.

## Key Features

### 1. Combined Timing and Memory Tracking
- Automatically measures elapsed time from entry to exit
- Tracks process memory (RSS) at probe points
- Minimal overhead - timing excludes the memory measurement itself

### 2. Probe System
The `probe(label: str)` method allows you to record measurements at specific points:
- **Time since start**: Cumulative time from the beginning
- **Time since last probe**: Time for just this step
- **Total memory**: Absolute RSS at this point
- **Memory delta from start**: Total memory change
- **Memory delta from last probe**: Memory change in this step

### 3. Automatic Reporting
When `verbose=True` (default), results are printed on exit in a formatted table:

```
======================================================================
Performance Measurement: My Test
======================================================================
Probe                     Time (s)     Δt (s)       Mem (MB)     ΔMem (MB)
----------------------------------------------------------------------
stage_opened                 0.1234     0.1234       1234.56      +123.45
sublayer_added               0.2456     0.1222       1345.67      +111.11
composition_forced           0.3678     0.1222       1456.78      +111.11
----------------------------------------------------------------------
TOTAL                        0.3678                                +234.56
======================================================================
```

### 4. Backward Compatibility
The legacy `result` attribute (MemoryResult) is still populated for existing code.

## Usage Examples

### Basic Usage with Probes

```python
from tests.benchmarks.results import PerformanceTracker

with PerformanceTracker(name="USD Load Test") as tracker:
    # Open base scene
    stage = Usd.Stage.Open("scene.usd")
    tracker.probe("stage_opened")
    
    # Add sublayer
    stage.GetRootLayer().subLayerPaths.append("props.usd")
    tracker.probe("sublayer_added")
    
    # Force composition
    _ = stage.GetPseudoRoot()
    tracker.probe("composition_forced")

# Results are automatically printed
```

### Silent Mode with Manual Access

```python
with PerformanceTracker(name="Test", verbose=False) as tracker:
    do_work()
    tracker.probe("step_1")
    
    do_more_work()
    tracker.probe("step_2")

# Access results programmatically
for probe in tracker.probes:
    print(f"{probe.label}: {probe.elapsed_since_last:.4f}s, "
          f"{probe.delta_since_last / (1024**2):+.2f} MB")
```

### Multiple Cold Runs

```python
times = []
for i in range(5):
    with PerformanceTracker(name=f"Run {i+1}", verbose=False) as tracker:
        load_and_process()
        tracker.probe("complete")
    
    times.append(tracker.probes[-1].elapsed_since_start)

print(f"Mean time: {sum(times) / len(times):.4f}s")
```

## ProbeResult Data Structure

Each probe returns and stores a `ProbeResult` with:

```python
@dataclass
class ProbeResult:
    label: str                    # User-provided label
    elapsed_since_start: float    # Seconds since tracker entry
    elapsed_since_last: float     # Seconds since last probe
    total_memory_bytes: int       # Current process RSS
    delta_since_start: int        # Memory change from start
    delta_since_last: int         # Memory change from last probe
```

## Implementation Details

### Timing Precision
- Uses `time.perf_counter()` for high-resolution timing
- **Probe overhead is automatically excluded**: The time spent measuring memory is tracked and subtracted from all timing calculations
- Each probe's `elapsed_since_start` excludes the cumulative overhead of all previous probes
- Each probe's `elapsed_since_last` naturally excludes overhead by measuring before memory checks
- Typical overhead: ~0.02-0.05ms per probe (negligible for most operations)

### Memory Tracking
- Tracks RSS (Resident Set Size) - the actual RAM used by the process
- Includes both Python and native (C++) allocations
- Works with `psutil` (preferred) or falls back to `resource` module
- Cross-platform (macOS, Linux, Windows with psutil)

### Cold Load Testing
For true cold load measurements:
1. Delete objects between runs (`del stage`)
2. Create fresh objects in each iteration
3. Use `verbose=False` except for the last run to reduce output

## See Also

- `examples/performance_tracker_usage.py` - Complete usage examples
- `tests/benchmarks/test_initial_load.py` - Real-world test using probes
- `tests/benchmarks/results.py` - Full implementation details
