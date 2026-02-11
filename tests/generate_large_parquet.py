import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def generate_large_parquet(
    filename="tests/data/large_test_data.parquet", target_size_mb=60
):
    """
    Generates a parquet file larger than the target size in MB.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Calculate number of rows needed roughly
    # Let's say we have 4 columns of doubles (8 bytes each) + string path
    # A generic row might be around 100 bytes.
    # 50MB = 50 * 1024 * 1024 bytes = 52,428,800 bytes
    # 52,428,800 / 100 ~= 524,288 rows.
    # To be safe and exceed compression, let's go for 2 million rows.

    num_rows = 1_000_000

    print(f"Generating data for {num_rows} rows...")

    # Generate data
    # We'll use a hierarchy of spheres
    paths = [f"/World/Sphere{i}" for i in range(num_rows)]

    data = {
        "path": paths,
        "temperature": np.random.uniform(20.0, 30.0, num_rows),
        "pressure": np.random.uniform(100.0, 200.0, num_rows),
        "velocity_x": np.random.normal(0, 1, num_rows),
        "velocity_y": np.random.normal(0, 1, num_rows),
        "velocity_z": np.random.normal(0, 1, num_rows),
    }

    df = pd.DataFrame(data)

    print("Converting to Table...")
    table = pa.Table.from_pandas(df)

    print(f"Writing to {filename}...")
    # Disable compression to reach size limit faster and faster write
    pq.write_table(table, filename, compression="NONE")

    file_size = os.path.getsize(filename) / (1024 * 1024)
    print(f"Generated {filename}: {file_size:.2f} MB")

    if file_size < target_size_mb:
        print(
            f"Warning: File size ({file_size:.2f} MB) is smaller than target ({target_size_mb} MB)."
        )
    else:
        print("Success: File size meets requirement.")


if __name__ == "__main__":
    generate_large_parquet()
