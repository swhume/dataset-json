"""
XPT writer for dsjconvert package.
This module provides functionality to write pandas DataFrames to SAS V5 XPORT (XPT) format
using pyreadstat.
"""
import logging
import pandas as pd
import pyreadstat
import datetime
from typing import Dict, List, Optional
from .exceptions import DatasetConversionError

logger = logging.getLogger(__name__)

class XPTWriter:
    """
    Writer for SAS V5 XPORT (XPT) format.
    Uses pyreadstat to write pandas DataFrames to XPT files with proper metadata.
    """

    def write(
        self,
        output_path: str,
        df: pd.DataFrame,
        metadata: Dict,
        table_name: Optional[str] = None,
        file_label: Optional[str] = None
    ) -> None:
        """
        Write DataFrame to XPT file.
        Args:
            output_path: Path where the XPT file should be written
            df: pandas DataFrame to write
            metadata: Dataset-JSON metadata dictionary
            table_name: Optional table name (defaults to metadata 'name')
            file_label: Optional file label (defaults to metadata 'label')
        Raises:
            DatasetConversionError: If writing fails
        """
        logger.debug(f"Writing XPT format to {output_path}")

        # Extract metadata
        if table_name is None:
            table_name = metadata.get('name', 'DATASET')

        if file_label is None:
            file_label = metadata.get('label', table_name)

        # Build column labels dictionary
        column_labels = {}
        columns_metadata = metadata.get('columns', [])
        for col_meta in columns_metadata:
            col_name = col_meta.get('name')
            col_label = col_meta.get('label', col_name)
            if col_name:
                column_labels[col_name] = col_label

        try:
            # If DataFrame is empty, set explicit dtypes from metadata to avoid
            # pyreadstat inferring from the first row (which doesn't exist).
            if df.empty:
                dtype_map = {}
                for col_meta in metadata.get('columns', []):
                    name = col_meta.get('name')
                    # Default to string if not provided
                    dtype = (col_meta.get('dataType') or 'string').lower()
                    if dtype in ('integer',):
                        # Use nullable integer to preserve missing values
                        dtype_map[name] = 'Int64'
                    elif dtype in ('double', 'float', 'numeric'):
                        dtype_map[name] = 'float64'
                    elif dtype in ('date', 'datetime', 'time'):
                        # SAS stores temporal values as numerics; use float64
                        dtype_map[name] = 'float64'
                    else:
                        # strings and all unknowns as object
                        dtype_map[name] = 'object'

                # Rebuild an empty DataFrame with desired dtypes in the correct order
                if dtype_map:
                    df = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in dtype_map.items()})
                    # Ensure column order matches metadata
                    ordered_cols = [c.get('name') for c in metadata.get('columns', []) if c.get('name') in df.columns]
                    df = df.reindex(columns=ordered_cols)

                # Prepare optional column widths for object columns (if supported)
                column_widths = {col: 40 for col, dt in dtype_map.items() if dt == 'object'}
            else:
                column_widths = None

            # Write to XPT using pyreadstat. Try passing column_widths if available.
            try:
                if column_widths:
                    pyreadstat.write_xport(
                        df,
                        output_path,
                        table_name=table_name,
                        file_label=file_label,
                        column_labels=column_labels,
                        column_widths=column_widths,
                        file_format_version=5
                    )
                else:
                    pyreadstat.write_xport(
                        df,
                        output_path,
                        table_name=table_name,
                        file_label=file_label,
                        column_labels=column_labels,
                        file_format_version=5
                    )
            except TypeError:
                # Older pyreadstat may not support column_widths parameter
                pyreadstat.write_xport(
                    df,
                    output_path,
                    table_name=table_name,
                    file_label=file_label,
                    column_labels=column_labels,
                    file_format_version=5
                )

            logger.info(
                f"Successfully wrote XPT dataset to {output_path}: "
                f"{len(df)} rows, {len(df.columns)} columns"
            )

        except Exception as e:
            logger.error(f"Failed to write XPT file: {e}")
            raise DatasetConversionError(
                table_name,
                f"Failed to write XPT file: {e}"
            )


def integer_to_datetime(value, data_type: str):
    """
    Convert Dataset-JSON numeric representation back to datetime objects.
    Dataset-JSON represents dates as:
    - Date: Days since 1960-01-01
    - DateTime: Days since 1960-01-01 + fractional day for time
    - Time: Fractional day (seconds_since_midnight / 86400)
    Args:
        value: Numeric value to convert
        data_type: Target data type ('date', 'datetime', 'time')
    Returns:
        datetime.date, datetime.datetime, or datetime.time object, or None
    Examples:
        >>> integer_to_datetime(0, 'date')
        datetime.date(1960, 1, 1)
        >>> integer_to_datetime(1, 'date')
        datetime.date(1960, 1, 2)
        >>> integer_to_datetime(0.5, 'time')
        datetime.time(12, 0, 0)
    """
    # Handle null values
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    epoch_date = datetime.date(1960, 1, 1)

    if data_type == 'date':
        # Convert days since epoch to date
        days = int(value)
        result_date = epoch_date + datetime.timedelta(days=days)
        logger.debug(f"Converted SAS integer {value} to date: {result_date}")
        return result_date

    elif data_type == 'datetime':
        # Convert days + fractional day to datetime
        days = int(value)
        fractional_day = value - days
        seconds = fractional_day * 86400

        result_date = epoch_date + datetime.timedelta(days=days)
        result_datetime = datetime.datetime.combine(
            result_date,
            datetime.time(0, 0, 0)
        ) + datetime.timedelta(seconds=seconds)

        logger.debug(f"Converted SAS float {value} to datetime: {result_datetime}")
        return result_datetime

    elif data_type == 'time':
        # Convert fractional day to time
        seconds = value * 86400
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        microseconds = int((seconds % 1) * 1e6)

        result_time = datetime.time(hours, minutes, secs, microseconds)
        logger.debug(f"Converted SAS float {value} to time: {result_time}")
        return result_time
    else:
        # Not a datetime type, return as-is
        return value


def convert_dataset_json_to_dataframe(metadata: Dict, rows: List[List]) -> pd.DataFrame:
    """
    Convert Dataset-JSON metadata and rows to a pandas DataFrame.
    Args:
        metadata: Dataset-JSON metadata dictionary
        rows: List of row data (each row is a list of values)
    Returns:
        pd.DataFrame: DataFrame with proper column names and types
    Raises:
        ValueError: If metadata or rows are invalid
    """
    columns_metadata = metadata.get('columns', [])
    if not columns_metadata:
        raise ValueError("Metadata must contain 'columns' field")

    # Extract column names and build type mapping
    column_names = []
    column_types = {}

    for col_meta in columns_metadata:
        col_name = col_meta.get('name')
        if not col_name:
            raise ValueError("Each column must have a 'name' field")

        column_names.append(col_name)
        column_types[col_name] = col_meta.get('dataType', 'string')

    # Create DataFrame from rows
    if not rows:
        # Empty dataset
        df = pd.DataFrame(columns=column_names)
    else:
        # Validate row lengths
        expected_length = len(column_names)
        for i, row in enumerate(rows):
            if len(row) != expected_length:
                raise ValueError(
                    f"Row {i} has {len(row)} values, expected {expected_length}"
                )

        df = pd.DataFrame(rows, columns=column_names)

    # Convert data types
    # Note: For XPT, we generally keep numeric types as-is since pyreadstat
    # handles the conversion. Date/datetime conversions can be added if needed.

    logger.debug(
        f"Converted Dataset-JSON to DataFrame: {len(df)} rows, {len(df.columns)} columns"
    )

    return df


def write_dataset_json_to_xpt(
    input_path: str,
    output_path: str,
    input_format: str = None
) -> None:
    """
    Convenience function to convert Dataset-JSON file to XPT.
    Args:
        input_path: Path to Dataset-JSON file
        output_path: Path where XPT file should be written
        input_format: Input format ('json' or 'ndjson'). If None, detected from extension.
    Raises:
        InvalidFormatError: If format is not supported
        DatasetReadError: If file cannot be read
        DatasetConversionError: If conversion fails
    """
    from .readers import read_dataset_json

    # Read Dataset-JSON
    metadata, rows = read_dataset_json(input_path, input_format)

    # Convert to DataFrame
    df = convert_dataset_json_to_dataframe(metadata, rows)

    # Write to XPT
    writer = XPTWriter()
    writer.write(output_path, df, metadata)
