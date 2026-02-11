#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#     "pandas",
#     "pyarrow",
# ]
# ///

import argparse
import sys

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="View parquet file contents.")
    parser.add_argument("path", help="Path to the parquet file")
    parser.add_argument("-n", type=int, default=10, help="Number of lines to print")

    args = parser.parse_args()

    try:
        df = pd.read_parquet(args.path)

        # Configure pandas display options for nicer formatting
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_rows", args.n)

        print(f"File: {args.path}")
        print(f"Shape: {df.shape}")
        print("-" * 40)
        print(f"Displaying top {args.n} rows:")
        print(df.head(args.n))
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
