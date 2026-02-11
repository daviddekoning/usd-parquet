"""
Test Case 1: File Size Comparison

Measures file sizes for all format variants (Parquet configurations + USDC).
"""

from pathlib import Path

import pytest

from .conftest import PARQUET_COMPRESSIONS, USDC_FORMAT
from .results import BenchmarkResult


class TestFileSize:
    """File size comparison tests."""

    def test_file_sizes(self, data_dir: Path, benchmark_scale: int, result_collector):
        """Measure and record file sizes for all format variants."""
        collector = result_collector

        # Build list of files to check based on current scale
        files_to_check = [
            (f"properties_{comp}_{benchmark_scale}.parquet", f"parquet_{comp}")
            for comp in PARQUET_COMPRESSIONS
        ] + [(USDC_FORMAT, "usdc")]

        for filename, format_name in files_to_check:
            path = data_dir / filename
            if not path.exists():
                pytest.skip(f"File not found: {path}")

            size_bytes = path.stat().st_size

            collector.add_file_size(format_name, size_bytes)

            # Also add as a result for detailed tracking
            collector.add_result(
                BenchmarkResult(
                    test_name="file_size",
                    format_name=format_name,
                    scale=collector.scale,
                    hierarchy=collector.hierarchy,
                    extra={
                        "size_bytes": size_bytes,
                        "size_mb": size_bytes / (1024 * 1024),
                    },
                )
            )

        # Print summary
        print("\nFile Size Summary:")
        print("-" * 50)
        for format_name, size in sorted(collector.file_sizes.items()):
            print(f"  {format_name}: {size / (1024 * 1024):.2f} MB")
