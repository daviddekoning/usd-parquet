from pxr import Sdf, Plug
import os
import pytest
import time


# Ensure the plugin is loaded
def setup_module(module):
    plugin = Plug.Registry().GetPluginWithName("parquetFormat")
    if plugin and not plugin.isLoaded:
        plugin.Load()


def test_large_parquet_file_loading():
    """
    Test loading a large (>50MB) parquet file.
    """
    large_file = os.path.abspath("tests/data/large_test_data.parquet")

    # Skip if file generation failed or wasn't run
    if not os.path.exists(large_file):
        pytest.skip(f"Large test file not found at {large_file}")

    print(f"Opening large file: {large_file}")
    start_time = time.time()

    # Open the layer directly
    layer = Sdf.Layer.FindOrOpen(large_file)
    assert layer is not None

    end_time = time.time()
    load_time = end_time - start_time
    print(f"Loaded large file in {load_time:.4f} seconds")

    # Basic assertions to ensure it's not empty and functional
    # We generated 1,000,000 rows, so we should expect paths like /World/Sphere0 ... /World/Sphere999999
    # Checking a few random ones.

    print("Checking /World/Sphere0")
    if not layer.GetPrimAtPath("/World/Sphere0"):
        print("FAILED to find /World/Sphere0")
    assert layer.GetPrimAtPath("/World/Sphere0")

    print("Checking /World/Sphere999999")
    if not layer.GetPrimAtPath("/World/Sphere999999"):
        print("FAILED to find /World/Sphere999999")
    assert layer.GetPrimAtPath("/World/Sphere999999")

    # Check a value
    prim = layer.GetPrimAtPath("/World/Sphere123456")
    # In Sdf, properties are children of the prim.
    # We can check if the property exists in the properties list or use layer.GetPropertyAtPath
    prop_path = prim.path.AppendProperty("temperature")
    assert layer.GetPropertyAtPath(prop_path) is not None

    # Verify value type (optional, but good sanity check)
    # This requires querying the attribute, which we can't easily do with high-level API on just Sdf.Layer
    # without Usd.Stage, but we can check if it's defined.
    print("Successfully verified existence of attribute 'temperature' on random prim.")
