"""
Core result collection utilities for benchmarks.
"""

import json
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Try to import psutil for accurate cross-platform memory tracking
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    # Fallback to resource module on Unix systems
    try:
        import resource

        HAS_RESOURCE = True
    except ImportError:
        HAS_RESOURCE = False

# Try to import UsdUtils to clear stage cache
try:
    from pxr import UsdUtils

    HAS_USD_UTILS = True
except ImportError:
    HAS_USD_UTILS = False


def flush_memory():
    """Force memory cleanup to ensure clean baseline for tests."""
    # 1. Force Python Garbage Collection
    import gc

    gc.collect()

    # 2. Clear USD Stage Cache
    if HAS_USD_UTILS:
        UsdUtils.StageCache.Get().Clear()


@dataclass
class TimingResult:
    """Statistics from multiple timing runs."""

    mean_seconds: float
    std_seconds: float
    min_seconds: float
    max_seconds: float
    run_count: int

    @classmethod
    def from_times(cls, times: list[float]) -> "TimingResult":
        """Create from a list of timing measurements."""
        return cls(
            mean_seconds=statistics.mean(times),
            std_seconds=statistics.stdev(times) if len(times) > 1 else 0.0,
            min_seconds=min(times),
            max_seconds=max(times),
            run_count=len(times),
        )


@dataclass
class MemoryResult:
    """Memory measurement result."""

    current_bytes: int
    peak_bytes: int


@dataclass
class ProbeResult:
    """Result from a single probe measurement.

    All timing values automatically exclude the overhead of memory measurement.
    The cumulative overhead from all previous probes is tracked and subtracted
    from elapsed_since_start to ensure accurate timing.
    """

    label: str
    # Timing (overhead-corrected)
    elapsed_since_start: float  # seconds since start (excludes all probe overhead)
    elapsed_since_last: (
        float  # seconds since last probe (excludes current probe overhead)
    )
    # Memory
    total_memory_bytes: int  # absolute RSS at this probe
    delta_since_start: int  # memory change since start
    delta_since_last: int  # memory change since last probe (or start)


@dataclass
class BenchmarkResult:
    """A single benchmark measurement."""

    test_name: str
    format_name: str
    scale: int
    hierarchy: str
    timing: TimingResult | None = None
    memory: MemoryResult | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BenchmarkTimer:
    """Context manager for timing with statistics."""

    def __init__(self, runs: int = 10, warmup: int = 1):
        self.runs = runs
        self.warmup = warmup
        self.times: list[float] = []

    def measure(
        self,
        func: Callable[..., Any],
        setup: Callable[[], Any] | None = None,
    ) -> TimingResult:
        """Run function multiple times and return timing statistics.

        Args:
            func: Function to time. If setup is provided, receives setup's return value.
            setup: Optional setup function called before each timed run. Its return
                   value is passed to func. Not included in timing. Use this to create
                   fresh stages with empty caches before each timing iteration.
        """
        # Warmup runs (discarded)
        for _ in range(self.warmup):
            if setup:
                ctx = setup()
                func(ctx)
            else:
                func()

        # Measured runs
        self.times = []
        for _ in range(self.runs):
            if setup:
                ctx = setup()
                start = time.perf_counter()
                func(ctx)
            else:
                start = time.perf_counter()
                func()
            elapsed = time.perf_counter() - start
            self.times.append(elapsed)

        return TimingResult.from_times(self.times)


class PerformanceTracker:
    """Context manager for tracking process-level memory and timing.
    
    This tracks the entire process memory (RSS - Resident Set Size), which
    includes C++ allocations from USD and other native libraries, not just
    Python allocations.
    
    Features:
    - Automatic timing from entry to exit
    - Memory tracking (RSS) throughout execution
    - Probe points to measure intermediate states
    - Detailed reporting of memory deltas and timing between probes
    
    Example:
        with PerformanceTracker() as tracker:
            # Do setup work
            stage = Usd.Stage.Open("scene.usd")
            tracker.probe("stage_opened")
            
            # Do more work
            stage.GetRootLayer().subLayerPaths.append("props.usd")
            tracker.probe("sublayer_added")
            
            _ = stage.GetPseudoRoot()
            tracker.probe("composition_forced")
        
        # Results printed automatically on exit
        # Or access via tracker.probes list
    """

    def __init__(self, name: str = "measurement", verbose: bool = True):
        """Initialize performance tracker.

        Args:
            name: Name for this measurement (used in output)
            verbose: If True, print results on exit
        """
        self.name = name
        self.verbose = verbose

        # Legacy result for backward compatibility
        self.result: MemoryResult | None = None

        # New probe-based results
        self.probes: list[ProbeResult] = []

        # Internal state
        self._start_time: float = 0
        self._start_memory: int = 0
        self._last_time: float = 0
        self._last_memory: int = 0
        self._total_probe_overhead: float = 0  # Accumulated measurement overhead

    def _get_process_memory(self) -> int:
        """Get current process RSS (Resident Set Size) in bytes."""
        if HAS_PSUTIL:
            # psutil provides cross-platform memory info
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        elif HAS_RESOURCE:
            # resource.getrusage on Unix (macOS/Linux)
            # ru_maxrss is in kilobytes on Linux, bytes on macOS
            import platform

            usage = resource.getrusage(resource.RUSAGE_SELF)
            if platform.system() == "Darwin":  # macOS
                return usage.ru_maxrss  # Already in bytes
            else:  # Linux
                return usage.ru_maxrss * 1024  # Convert KB to bytes
        else:
            # No memory tracking available
            return 0

    def __enter__(self):
        """Start measurement."""
        self._start_time = time.perf_counter()
        self._start_memory = self._get_process_memory()
        self._last_time = self._start_time
        self._last_memory = self._start_memory
        return self

    def probe(self, label: str) -> ProbeResult:
        """Record a measurement probe at this point in execution.

        The probe measures timing before and after the memory check,
        excluding the measurement overhead from the reported elapsed times.
        The overhead is tracked and accumulated so that elapsed_since_start
        remains accurate across multiple probes.

        Args:
            label: Descriptive label for this probe point

        Returns:
            ProbeResult with timing and memory deltas
        """
        # Measure time before memory check
        time_before = time.perf_counter()

        # Get memory (this may take a moment)
        current_memory = self._get_process_memory()

        # Measure time after memory check
        time_after = time.perf_counter()
        measurement_overhead = time_after - time_before

        # Accumulate total overhead
        self._total_probe_overhead += measurement_overhead

        # Calculate timing (excluding all accumulated measurement overhead)
        elapsed_since_start = (
            time_before - self._start_time - self._total_probe_overhead
        )
        elapsed_since_last = time_before - self._last_time

        # Calculate memory deltas
        delta_since_start = current_memory - self._start_memory
        delta_since_last = current_memory - self._last_memory

        probe = ProbeResult(
            label=label,
            elapsed_since_start=elapsed_since_start,
            elapsed_since_last=elapsed_since_last,
            total_memory_bytes=current_memory,
            delta_since_start=delta_since_start,
            delta_since_last=delta_since_last,
        )

        self.probes.append(probe)

        # Update last measurements (use time_after to account for overhead in next delta)
        self._last_time = time_after
        self._last_memory = current_memory

        return probe

    def __exit__(self, *args):
        """Finish measurement and optionally print results."""
        # Take final measurement
        end_time = time.perf_counter()
        end_memory = self._get_process_memory()

        # Calculate totals
        total_elapsed = end_time - self._start_time
        total_delta = end_memory - self._start_memory

        # Set legacy result for backward compatibility
        self.result = MemoryResult(
            current_bytes=max(0, total_delta), peak_bytes=max(0, total_delta)
        )

        # Print results if verbose
        if self.verbose and self.probes:
            self._print_results(total_elapsed, total_delta)

    def _print_results(self, total_elapsed: float, total_delta: int):
        """Print formatted probe results."""
        print(f"\n{'=' * 70}")
        print(f"Performance Measurement: {self.name}")
        print(f"{'=' * 70}")
        print(
            f"{'Probe':<25} {'Time (s)':<12} {'Δt (s)':<12} {'Mem (MB)':<12} {'ΔMem (MB)':<12}"
        )
        print(f"{'-' * 70}")

        for probe in self.probes:
            print(
                f"{probe.label:<25} "
                f"{probe.elapsed_since_start:>10.4f}  "
                f"{probe.elapsed_since_last:>10.4f}  "
                f"{probe.total_memory_bytes / (1024 * 1024):>10.2f}  "
                f"{probe.delta_since_last / (1024 * 1024):>+10.2f}"
            )

        print(f"{'-' * 70}")
        print(
            f"{'TOTAL':<25} "
            f"{total_elapsed:>10.4f}  "
            f"{'':>10}  "
            f"{'':>10}  "
            f"{total_delta / (1024 * 1024):>+10.2f}"
        )
        print(f"{'=' * 70}\n")


class ResultCollector:
    """Collects benchmark results for later output."""

    def __init__(self, scale: int, hierarchy: str):
        self.scale = scale
        self.hierarchy = hierarchy
        self.results: list[BenchmarkResult] = []
        self.file_sizes: dict[str, int] = {}
        self.test_run = datetime.now().isoformat()

    def add_file_size(self, format_name: str, size_bytes: int) -> None:
        """Record a file size measurement."""
        self.file_sizes[format_name] = size_bytes

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_run": self.test_run,
            "scale": self.scale,
            "hierarchy": self.hierarchy,
            "file_sizes": self.file_sizes,
            "results": [
                {
                    "test": r.test_name,
                    "format": r.format_name,
                    "mean_seconds": r.timing.mean_seconds if r.timing else None,
                    "std_seconds": r.timing.std_seconds if r.timing else None,
                    "min_seconds": r.timing.min_seconds if r.timing else None,
                    "max_seconds": r.timing.max_seconds if r.timing else None,
                    "run_count": r.timing.run_count if r.timing else None,
                    "current_memory_bytes": r.memory.current_bytes
                    if r.memory
                    else None,
                    "peak_memory_bytes": r.memory.peak_bytes if r.memory else None,
                    **r.extra,
                }
                for r in self.results
            ],
        }

    def save_json(self, output_path: Path) -> None:
        """Save results to JSON file."""
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"Results saved to {output_path}")


# Global collector instance (set by conftest.py)
_collector: ResultCollector | None = None


def get_collector() -> ResultCollector:
    """Get the global result collector."""
    if _collector is None:
        raise RuntimeError("ResultCollector not initialized. Run via pytest.")
    return _collector


def set_collector(collector: ResultCollector) -> None:
    """Set the global result collector."""
    global _collector
    _collector = collector
