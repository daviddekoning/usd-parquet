"""
Pytest configuration and fixtures for benchmark tests.
"""

from pathlib import Path

import pytest
from pxr import Plug

from .results import ResultCollector, set_collector

# Default test configuration
DEFAULT_SCALE = 1000
DEFAULT_HIERARCHY = "flat"

# Compression variants to test (scale comes from --benchmark-scale)
PARQUET_COMPRESSIONS = ["zstd"]
USDC_FORMAT = "properties.usdc"

# Properties to test (subset for multi-property tests)
TEST_PROPERTIES = [
    "cost",
    "carbon_A1",
    "weight",
    "temperature",
    "is_active",
    "supplier_id",
]


def pytest_addoption(parser):
    """Add command line options for benchmark configuration."""
    parser.addoption(
        "--benchmark-scale",
        type=int,
        default=DEFAULT_SCALE,
        help="Number of prims in test data",
    )
    parser.addoption(
        "--benchmark-hierarchy",
        type=str,
        default=DEFAULT_HIERARCHY,
        choices=["flat", "deep"],
        help="Hierarchy pattern",
    )


@pytest.fixture(scope="session")
def benchmark_scale(request) -> int:
    """Get the benchmark scale from command line."""
    return request.config.getoption("--benchmark-scale")


@pytest.fixture(scope="session")
def benchmark_hierarchy(request) -> str:
    """Get the hierarchy pattern from command line."""
    return request.config.getoption("--benchmark-hierarchy")


@pytest.fixture(scope="session")
def data_dir(benchmark_scale, benchmark_hierarchy) -> Path:
    """Get the data directory for the current test configuration."""
    base = Path(__file__).parent.parent / "data" / "benchmarks"
    return base / f"{benchmark_scale}_{benchmark_hierarchy}"


@pytest.fixture(scope="session", autouse=True)
def ensure_plugin_loaded():
    """Ensure the parquet plugin is loaded before tests."""
    plugin = Plug.Registry().GetPluginWithName("parquetFormat")
    if plugin and not plugin.isLoaded:
        plugin.Load()


@pytest.fixture(scope="session")
def result_collector(benchmark_scale, benchmark_hierarchy, data_dir) -> ResultCollector:
    """Create and set up the global result collector."""
    collector = ResultCollector(scale=benchmark_scale, hierarchy=benchmark_hierarchy)
    set_collector(collector)
    yield collector
    # Save results at end of session
    output_path = data_dir / "benchmark_results.json"
    collector.save_json(output_path)


@pytest.fixture(scope="session")
def base_scene_path(data_dir) -> Path:
    """Path to the base scene USDA file."""
    path = data_dir / "base_scene.usda"
    if not path.exists():
        pytest.skip(f"Base scene not found: {path}. Run generate_test_data.py first.")
    return path


@pytest.fixture(params=PARQUET_COMPRESSIONS + ["usdc"])
def property_file(request, data_dir, benchmark_scale) -> tuple[str, Path]:
    """
    Parametrized fixture yielding (format_name, path) for each format variant.
    Scale is determined by --benchmark-scale to match the base layer.
    """
    compression = request.param

    if compression == "usdc":
        filename = USDC_FORMAT
        format_name = "usdc"
    else:
        filename = f"properties_{compression}_{benchmark_scale}.parquet"
        format_name = f"parquet_{compression}"

    path = data_dir / filename
    if not path.exists():
        pytest.skip(f"Test data not found: {path}. Run generate_test_data.py first.")

    return format_name, path


@pytest.fixture(params=PARQUET_COMPRESSIONS)
def parquet_file(request, data_dir, benchmark_scale) -> tuple[str, Path]:
    """
    Parametrized fixture yielding (format_name, path) for each Parquet variant only.
    Scale is determined by --benchmark-scale to match the base layer.
    """
    compression = request.param
    filename = f"properties_{compression}_{benchmark_scale}.parquet"
    format_name = f"parquet_{compression}"

    path = data_dir / filename
    if not path.exists():
        pytest.skip(f"Test data not found: {path}. Run generate_test_data.py first.")

    return format_name, path


@pytest.fixture
def usdc_file(data_dir) -> tuple[str, Path]:
    """Fixture for the USDC file."""
    path = data_dir / USDC_FORMAT
    if not path.exists():
        pytest.skip(f"USDC file not found: {path}. Run generate_test_data.py first.")
    return "usdc", path
