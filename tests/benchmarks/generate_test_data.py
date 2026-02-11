#!/usr/bin/env python3
"""
Generate test data for Parquet vs USDC benchmarks.

By default, existing files are preserved to speed up development iteration.
Use --force to regenerate all files.

Usage:
    uv run python tests/benchmarks/generate_test_data.py --scale 1000 --hierarchy flat
    uv run python tests/benchmarks/generate_test_data.py --scale 1000 --hierarchy flat --force
"""

import argparse
import os
import random
import string
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Property definitions matching benchmark_spec.md
PROPERTIES = {
    # Doubles (14)
    "cost": ("double", lambda n: np.random.uniform(100, 10000, n)),
    "carbon_A1": ("double", lambda n: np.random.uniform(0, 100, n)),
    "carbon_A2": ("double", lambda n: np.random.uniform(0, 50, n)),
    "carbon_A3": ("double", lambda n: np.random.uniform(0, 200, n)),
    "carbon_A4": ("double", lambda n: np.random.uniform(0, 30, n)),
    "carbon_A5": ("double", lambda n: np.random.uniform(0, 20, n)),
    "weight": ("double", lambda n: np.random.uniform(1, 1000, n)),
    "temperature": ("double", lambda n: np.random.uniform(-20, 60, n)),
    "pressure": ("double", lambda n: np.random.uniform(90000, 110000, n)),
    "velocity_x": ("double", lambda n: np.random.normal(0, 1, n)),
    "velocity_y": ("double", lambda n: np.random.normal(0, 1, n)),
    "velocity_z": ("double", lambda n: np.random.normal(0, 1, n)),
    "stress": ("double", lambda n: np.random.uniform(0, 500, n)),
    "strain": ("double", lambda n: np.random.uniform(0, 0.01, n)),
    "efficiency": ("double", lambda n: np.random.uniform(0.5, 1.0, n)),
    # Int (1)
    "lifespan": ("int", lambda n: np.random.randint(1, 50, n)),
    # Bool (1)
    "is_active": ("bool", lambda n: np.random.choice([True, False], n)),
    # Strings (4)
    "supplier_id": (
        "string",
        lambda n: [f"SUP-{random.randint(1000, 9999)}" for _ in range(n)],
    ),
    "material_code": (
        "string",
        lambda n: [
            "".join(random.choices(string.ascii_uppercase, k=3))
            + "-"
            + str(random.randint(100, 999))
            for _ in range(n)
        ],
    ),
    "install_date": (
        "string",
        lambda n: [
            f"20{random.randint(20, 25):02d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            for _ in range(n)
        ],
    ),
    # Large payload for memory testing (1KB per prim) - random characters
    "payload": (
        "string",
        lambda n: [
            "".join(random.choices(string.ascii_letters + string.digits, k=1000))
            for _ in range(n)
        ],
    ),
}

# Parquet configurations to test
COMPRESSIONS = ["ZSTD"]
ROW_GROUP_SIZES = [100, 1000, 10000]


def generate_paths(n: int, hierarchy: str) -> list[str]:
    """Generate prim paths based on hierarchy pattern."""
    if hierarchy == "flat":
        return [f"/World/Prim_{i}" for i in range(n)]
    elif hierarchy == "deep":
        # 4-level deep hierarchy: Zone/Level/Room/Component
        paths = []
        zones = max(1, n // 1000)
        levels = 10
        rooms = 10
        components_per_room = max(1, n // (zones * levels * rooms))

        idx = 0
        for z in range(zones):
            for l in range(levels):
                for r in range(rooms):
                    for c in range(components_per_room):
                        if idx >= n:
                            break
                        paths.append(
                            f"/World/Zone_{z}/Level_{l}/Room_{r}/Component_{c}"
                        )
                        idx += 1
                    if idx >= n:
                        break
                if idx >= n:
                    break
            if idx >= n:
                break

        # Fill remaining if needed
        while len(paths) < n:
            paths.append(f"/World/Extra/Prim_{len(paths)}")

        return paths[:n]
    else:
        raise ValueError(f"Unknown hierarchy: {hierarchy}")


def generate_dataframe(n: int, hierarchy: str) -> pd.DataFrame:
    """Generate a DataFrame with all properties."""
    print(f"Generating DataFrame with {n} rows...")

    data = {"path": generate_paths(n, hierarchy)}

    for prop_name, (_, generator) in PROPERTIES.items():
        data[prop_name] = generator(n)

    return pd.DataFrame(data)


def write_parquet(
    df: pd.DataFrame, output_path: Path, compression: str, row_group_size: int, force: bool = False
) -> bool:
    """Write DataFrame to Parquet with specified settings.
    
    Returns True if file was written, False if skipped (already exists).
    """
    if output_path.exists() and not force:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Skipped: {output_path.name} ({size_mb:.2f} MB) - already exists")
        return False
    
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        output_path,
        compression=compression if compression != "NONE" else None,
        row_group_size=row_group_size,
    )
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Written: {output_path.name} ({size_mb:.2f} MB)")
    return True


def write_usdc(df: pd.DataFrame, output_path: Path, force: bool = False) -> bool:
    """Write DataFrame as a USDC layer with 'over' prims.
    
    Returns True if file was written, False if skipped (already exists).
    """
    if output_path.exists() and not force:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Skipped: {output_path.name} ({size_mb:.2f} MB) - already exists")
        return False
    
    from pxr import Sdf, Vt

    # Create layer
    layer = Sdf.Layer.CreateNew(str(output_path))

    for _, row in df.iterrows():
        path = row["path"]
        prim_path = Sdf.Path(path)

        # Create prim spec as 'over'
        prim_spec = Sdf.CreatePrimInLayer(layer, prim_path)
        prim_spec.specifier = Sdf.SpecifierOver

        # Add attributes
        for prop_name, (type_name, _) in PROPERTIES.items():
            value = row[prop_name]

            # Create attribute spec
            attr_spec = Sdf.AttributeSpec(
                prim_spec,
                prop_name,
                Sdf.ValueTypeNames.Find(_get_sdf_type_name(type_name)),
            )

            # Set default value
            attr_spec.default = _convert_value(value, type_name)

    layer.Save()
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Written: {output_path.name} ({size_mb:.2f} MB)")
    return True


def _get_sdf_type_name(type_name: str) -> str:
    """Map our type names to SDF type names."""
    mapping = {
        "double": "double",
        "int": "int",
        "bool": "bool",
        "string": "string",
    }
    return mapping[type_name]


def _convert_value(value, type_name: str):
    """Convert numpy/python values to USD-compatible values."""
    if type_name == "double":
        return float(value)
    elif type_name == "int":
        return int(value)
    elif type_name == "bool":
        return bool(value)
    elif type_name == "string":
        return str(value)
    return value


def write_base_usda(paths: list[str], output_path: Path, force: bool = False) -> bool:
    """Write a base USDA file with prim hierarchy but no properties.
    
    Returns True if file was written, False if skipped (already exists).
    """
    if output_path.exists() and not force:
        print(f"  Skipped: {output_path.name} - already exists")
        return False
    
    from pxr import Sdf

    layer = Sdf.Layer.CreateNew(str(output_path))
    
    # Ensure root prim is defined so Traversal works
    root_path = Sdf.Path(paths[0]).GetPrefixes()[0]
    root_prim = Sdf.CreatePrimInLayer(layer, root_path)
    root_prim.specifier = Sdf.SpecifierDef
    root_prim.typeName = "Xform"

    for path in paths:
        prim_path = Sdf.Path(path)
        prim_spec = Sdf.CreatePrimInLayer(layer, prim_path)
        prim_spec.specifier = Sdf.SpecifierDef
        prim_spec.typeName = "Xform"

    layer.Save()
    print(f"  Written: {output_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark test data")
    parser.add_argument(
        "--scale",
        type=int,
        default=1000,
        choices=[1000, 10000, 100000, 1000000],
        help="Number of prims to generate",
    )
    parser.add_argument(
        "--hierarchy",
        type=str,
        default="flat",
        choices=["flat", "deep"],
        help="Hierarchy pattern",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/data/benchmarks",
        help="Output directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of existing files",
    )
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir) / f"{args.scale}_{args.hierarchy}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    if args.force:
        print("Force mode: Will regenerate all files")
    else:
        print("Incremental mode: Will skip existing files (use --force to regenerate)")

    # Check if we need to generate data at all
    needs_generation = args.force
    if not needs_generation:
        # Check if any required files are missing
        base_path = output_dir / "base_scene.usda"
        usdc_path = output_dir / "properties.usdc"
        required_files = [base_path, usdc_path]
        
        for compression in COMPRESSIONS:
            filename = f"properties_{compression.lower()}_{args.scale}.parquet"
            required_files.append(output_dir / filename)
        
        for file_path in required_files:
            if not file_path.exists():
                needs_generation = True
                break
    
    if not needs_generation:
        print("\n✓ All files already exist. Skipping generation.")
        print("  Use --force to regenerate.")
        return

    # Generate data only if needed
    print(f"\nGenerating DataFrame with {args.scale} rows...")
    df = generate_dataframe(args.scale, args.hierarchy)

    # Write base USDA (hierarchy only)
    print("\nWriting base USDA...")
    base_path = output_dir / "base_scene.usda"
    write_base_usda(df["path"].tolist(), base_path, args.force)

    # Replace all occurrences of the word 'over' with 'def' in the USDA file
    # yes, I know this is a dirty hack
    print("\nPost-processing USDA: replacing 'over' with 'def'...")
    try:
        original = base_path.read_text(encoding="utf-8")
        updated, count = re.subn(r"\bover\b", "def", original)
        if count > 0:
            base_path.write_text(updated, encoding="utf-8")
            print(f"  Replaced {count} occurrence(s) in {base_path.name}")
        else:
            print("  No 'over' occurrences found in USDA")
    except Exception as e:
        print(f"  Warning: failed to update {base_path.name}: {e}")

    # Write Parquet variants
    print("\nWriting Parquet files...")
    written_count = 0
    for compression in COMPRESSIONS:
        filename = f"properties_{compression.lower()}_{args.scale}.parquet"
        # Use smaller row groups to see progressive loading effect
        if write_parquet(df, output_dir / filename, compression, 50, args.force):
            written_count += 1

    # Write USDC
    print("\nWriting USDC file...")
    write_usdc(df, output_dir / "properties.usdc", args.force)

    print(f"\n✓ Done! Output in {output_dir}")
    if not args.force and written_count < len(COMPRESSIONS):
        print(f"  ({len(COMPRESSIONS) - written_count} file(s) were skipped - already exist)")


if __name__ == "__main__":
    main()
