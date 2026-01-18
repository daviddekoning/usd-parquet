import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os


def create_parquet():
    data = {
        "path": ["/World/Sphere1", "/World/Sphere2", "/World/Sphere3"],
        "temperature": [25.5, 30.2, 22.1],
        "velocity_x": [1.0, 2.0, 3.0],
        "velocity_y": [0.5, 0.7, 0.9],
    }

    df = pd.DataFrame(data)

    # Create directory if doesn't exist
    os.makedirs("tests/data", exist_ok=True)

    table = pa.Table.from_pandas(df)
    pq.write_table(
        table, "tests/data/test_data.parquet", row_group_size=1
    )  # Small row group for testing lazy load

    print(f"Created tests/data/test_data.parquet with {len(df)} rows.")


if __name__ == "__main__":
    create_parquet()
