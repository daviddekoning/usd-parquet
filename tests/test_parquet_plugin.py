from pxr import Sdf, Usd, Plug
import os
import sys


def test_parquet_plugin():
    print(f"USD Version: {Usd.GetVersion()}")

    # Check plugin loaded
    plugin = Plug.Registry().GetPluginWithName("parquetFormat")
    assert plugin is not None
    if not plugin.isLoaded:
        plugin.Load()
    assert plugin.isLoaded
    print("Plugin loaded successfully")

    # Open parquet file directly
    layer = Sdf.Layer.FindOrOpen("tests/data/test_data.parquet")
    assert layer is not None
    print("Layer opened successfully")

    # Verify hierarchy
    assert layer.GetPrimAtPath("/World")
    assert layer.GetPrimAtPath("/World/Sphere1")
    assert layer.GetPrimAtPath("/World/Sphere2")
    print("Hierarchy verified")

    # Create a composition stage to test value resolution
    base_layer = Sdf.Layer.CreateAnonymous()
    base_layer.ImportFromString("""#usda 1.0
def "World" {
    def "Sphere1" {
        float temperature = 0
        float velocity_x = 0
    }
    def "Sphere2" {
        float temperature = 0
    }
}
""")

    root_layer = Sdf.Layer.CreateAnonymous()
    # Parquet layer must be stronger to override defaults
    root_layer.subLayerPaths.append(layer.identifier)
    root_layer.subLayerPaths.append(base_layer.identifier)

    stage = Usd.Stage.Open(root_layer)
    assert stage
    print("Stage created")

    # Test values
    sphere1 = stage.GetPrimAtPath("/World/Sphere1")
    assert sphere1.IsValid()

    temp = sphere1.GetAttribute("temperature")
    assert temp.IsValid()
    val = temp.Get()
    print(f"/World/Sphere1.temperature = {val}")
    assert abs(val - 25.5) < 0.001

    vel_x = sphere1.GetAttribute("velocity_x")
    val = vel_x.Get()
    print(f"/World/Sphere1.velocity_x = {val}")
    assert abs(val - 1.0) < 0.001

    print("All tests passed!")


if __name__ == "__main__":
    test_parquet_plugin()
