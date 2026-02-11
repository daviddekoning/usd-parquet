#!/usr/bin/env python3
"""
Run complete benchmark suite across all scales and hierarchies.

This is the main entry point for running the full Parquet vs USDC benchmark comparison.

Usage:
    # Set environment variables first
    export PYTHONPATH=~/OpenUSD-25.11-install/lib/python
    export PXR_PLUGINPATH_NAME=$(pwd)/build/resources

    # Run full suite
    uv run python tests/benchmarks/run_benchmarks.py

    # Run specific scales only
    uv run python tests/benchmarks/run_benchmarks.py --scales 1000 10000

    # Skip data generation (if already exists)
    uv run python tests/benchmarks/run_benchmarks.py --skip-generate
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Benchmark configurations
SCALES = [1000, 10000, 100000]
HIERARCHIES = ["flat", "deep"]


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"🔹 {description}")
    print(f"{'=' * 60}")
    print(f"$ {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    return result.returncode == 0


def generate_test_data(scale: int, hierarchy: str) -> bool:
    """Generate test data for a specific scale and hierarchy."""
    return run_command(
        [
            "uv",
            "run",
            "python",
            "tests/benchmarks/generate_test_data.py",
            "--scale",
            str(scale),
            "--hierarchy",
            hierarchy,
        ],
        f"Generating test data: {scale} prims, {hierarchy} hierarchy",
    )


def run_benchmarks(scale: int, hierarchy: str, test_filter: str | None = None) -> bool:
    """Run pytest benchmarks for a specific scale and hierarchy."""
    cmd = [
        "uv",
        "run",
        "pytest",
        "tests/benchmarks/",
        "-v",
        f"--benchmark-scale={scale}",
        f"--benchmark-hierarchy={hierarchy}",
    ]

    if test_filter:
        cmd.extend(["-k", test_filter])

    return run_command(
        cmd,
        f"Running benchmarks: {scale} prims, {hierarchy} hierarchy"
        + (f" (filter: {test_filter})" if test_filter else ""),
    )


def generate_report(scale: int, hierarchy: str) -> bool:
    """Generate HTML report for a specific scale and hierarchy."""
    return run_command(
        [
            "uv",
            "run",
            "python",
            "tests/benchmarks/report.py",
            "--scale",
            str(scale),
            "--hierarchy",
            hierarchy,
        ],
        f"Generating report: {scale} prims, {hierarchy} hierarchy",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run complete Parquet vs USDC benchmark suite"
    )
    parser.add_argument(
        "--scales",
        type=int,
        nargs="+",
        default=SCALES,
        help=f"Scales to test (default: {SCALES})",
    )
    parser.add_argument(
        "--hierarchies",
        type=str,
        nargs="+",
        default=HIERARCHIES,
        choices=HIERARCHIES,
        help=f"Hierarchies to test (default: {HIERARCHIES})",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip test data generation (use existing files)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (only generate data and reports)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Run only tests matching this string pattern (e.g. 'initial_load')",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 Parquet vs USDC Benchmark Suite")
    print("=" * 60)
    print(f"Scales: {args.scales}")
    print(f"Hierarchies: {args.hierarchies}")
    print(f"Total configurations: {len(args.scales) * len(args.hierarchies)}")

    results = []

    for scale in args.scales:
        for hierarchy in args.hierarchies:
            config = f"{scale}_{hierarchy}"
            print(f"\n\n{'#' * 60}")
            print(f"# Configuration: {config}")
            print(f"{'#' * 60}")

            # Generate test data
            if not args.skip_generate:
                if not generate_test_data(scale, hierarchy):
                    print(f"❌ Failed to generate data for {config}")
                    results.append((config, "GENERATE_FAILED"))
                    continue

            # Run benchmarks
            if not args.skip_tests:
                if not run_benchmarks(scale, hierarchy, args.filter):
                    print(f"❌ Benchmarks failed for {config}")
                    results.append((config, "TESTS_FAILED"))
                    continue

            # Generate report
            if not generate_report(scale, hierarchy):
                print(f"⚠️  Report generation failed for {config}")
                results.append((config, "REPORT_FAILED"))
                continue

            results.append((config, "SUCCESS"))
            print(f"\n✅ Completed: {config}")

    # Summary
    print("\n\n" + "=" * 60)
    print("📊 BENCHMARK SUITE SUMMARY")
    print("=" * 60)

    successes = [r for r in results if r[1] == "SUCCESS"]
    failures = [r for r in results if r[1] != "SUCCESS"]

    print(f"\n✅ Successful: {len(successes)}/{len(results)}")
    for config, _ in successes:
        report_path = f"tests/data/benchmarks/{config}/benchmark_report.html"
        print(f"   - {config}: {report_path}")

    if failures:
        print(f"\n❌ Failed: {len(failures)}/{len(results)}")
        for config, status in failures:
            print(f"   - {config}: {status}")

    print("\n" + "=" * 60)
    print("To view reports, open the HTML files in a browser:")
    print("  open tests/data/benchmarks/*/benchmark_report.html")
    print("=" * 60)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
