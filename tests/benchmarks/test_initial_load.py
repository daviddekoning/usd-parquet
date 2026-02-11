"""
Test Case 2: Initial Sublayer Load (Cold Load)

Measures time and memory for cold loading a property sublayer into a stage.
Uses probes to measure different stages of the loading process.
"""

import multiprocessing
import time
import pytest
from pathlib import Path

from pxr import Usd

from .results import BenchmarkResult, TimingResult, MemoryTracker, MemoryResult


def _run_single_iteration(base_scene_path_str, prop_path_str, format_name, run_index, result_queue):
    """Run a single iteration in a separate process."""
    try:
        with MemoryTracker(name=f"{format_name} Run {run_index}", verbose=False) as tracker:
            # 1. Start probe (baseline)
            tracker.probe("start")

            # 2. Open base scene (loads base layer)
            stage = Usd.Stage.Open(base_scene_path_str)
            root_layer = stage.GetRootLayer()
            tracker.probe("base_layer_loaded")
            
            # 3. Add property sublayer
            root_layer.subLayerPaths.append(prop_path_str)
            tracker.probe("sublayer_added")
            
            # 4. Force composition
            _ = stage.GetPseudoRoot()
            tracker.probe("composition_complete")
        
        result_queue.put(tracker.probes)
        
    except Exception as e:
        # Pass exception back to main process
        result_queue.put(e)


class TestInitialLoad:
    """Initial sublayer load performance tests (cold load)."""

    @pytest.mark.skip(reason="Covered by traverse test")
    def test_initial_load(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure time and memory for cold loading property sublayer into stage.
        
        This is a simplified cold-load test that:
        - Makes 5 independent runs (no warmup)
        - Measures both timing and memory at key points via probes
        - Each run starts fresh with clean USD caches
        """
        format_name, prop_path = property_file
        collector = result_collector
        
        num_runs = 5
        times = []
        memory_peaks = []
        all_probe_data = []
        
        print(f"\n{'='*70}")
        print(f"{format_name} cold sublayer load ({num_runs} runs)")
        print(f"{'='*70}\n")
        
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}:")
            
            # Use multiprocessing to isolate memory and run clean
            queue = multiprocessing.Queue()
            
            p = multiprocessing.Process(
                target=_run_single_iteration,
                args=(str(base_scene_path), str(prop_path), format_name, i+1, queue)
            )
            p.start()
            
            try:
                # Wait for result (timeout 60s)
                probes = queue.get(timeout=60)
                p.join()
                
                if isinstance(probes, Exception):
                    raise probes
                
                if probes:
                    # Calculate results from probes
                    total_time = probes[-1].elapsed_since_start
                    total_memory = probes[-1].delta_since_start
                    
                    times.append(total_time)
                    memory_peaks.append(total_memory)
                    
                    # Convert probes to dictionary format for storage
                    run_probes = []
                    for probe in probes:
                        run_probes.append({
                            "label": probe.label,
                            "elapsed_since_start": probe.elapsed_since_start,
                            "elapsed_since_last": probe.elapsed_since_last,
                            "total_memory_bytes": probe.total_memory_bytes,
                            "delta_since_start": probe.delta_since_start,
                            "delta_since_last": probe.delta_since_last
                        })
                    all_probe_data.append(run_probes)
                    
                    if i < num_runs - 1:
                        print(f"  Total: {total_time:.4f}s, {total_memory / (1024*1024):+.2f} MB\n")
            
            except Exception as e:
                if p.is_alive():
                    p.terminate()
                raise e
        
        # Calculate statistics across all runs
        timing = TimingResult.from_times(times)
        
        # Create memory result from average peak
        avg_peak = sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0
        final_memory = MemoryResult(current_bytes=int(avg_peak), peak_bytes=int(avg_peak))
        
        # Add result to collector
        collector.add_result(
            BenchmarkResult(
                test_name="initial_load_cold",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                memory=final_memory,
                extra={"detailed_probes": all_probe_data},
            )
        )
        
        # Print overall summary
        print(f"\n{'='*70}")
        print(f"Overall Summary: {format_name}")
        print(f"{'='*70}")
        print(f"Timing Statistics ({num_runs} runs):")
        print(f"  Mean:  {timing.mean_seconds:.4f}s")
        print(f"  Std:   {timing.std_seconds:.4f}s")
        print(f"  Range: [{timing.min_seconds:.4f}s - {timing.max_seconds:.4f}s]")
        print(f"\nMemory Statistics:")
        print(f"  Avg Peak: {avg_peak / (1024 * 1024):+.2f} MB")
        if memory_peaks:
            min_mem = min(memory_peaks) / (1024 * 1024)
            max_mem = max(memory_peaks) / (1024 * 1024)
            print(f"  Range:    [{min_mem:+.2f} MB - {max_mem:+.2f} MB]")
        print(f"{'='*70}\n")
