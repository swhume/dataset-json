"""
Utility functions for dsjconvert package.

This module contains helper functions for data type conversions,
particularly for converting datetime objects to SAS date representations.
"""

import datetime
import logging

logger = logging.getLogger(__name__)


def datetime_to_integer(dt):
    """
    Convert datetime object to SAS date representation.

    SAS dates are represented as:
    - Date: Days since 1960-01-01
    - DateTime: Days since 1960-01-01 + fractional day for time
    - Time: Fractional day (seconds_since_midnight / 86400)

    Args:
        dt: A datetime.date, datetime.datetime, or datetime.time object

    Returns:
        float or int: SAS date representation

    Raises:
        TypeError: If dt is not a recognized datetime type

    Examples:
        >>> datetime_to_integer(datetime.date(1960, 1, 1))
        0
        >>> datetime_to_integer(datetime.date(1960, 1, 2))
        1
        >>> datetime_to_integer(datetime.time(12, 0, 0))  # Noon
        0.5
    """
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        # For date objects, convert to SAS date representation
        days_since_epoch = (dt - datetime.date(1960, 1, 1)).days
        logger.debug(f"Converted date {dt} to SAS integer: {days_since_epoch}")
        return days_since_epoch

    elif isinstance(dt, datetime.datetime):
        # For datetime objects, convert to SAS date representation
        days_since_epoch = (dt.date() - datetime.date(1960, 1, 1)).days
        seconds_since_midnight = (
            dt.hour * 3600 +
            dt.minute * 60 +
            dt.second +
            dt.microsecond / 1e6
        )
        sas_datetime = days_since_epoch + seconds_since_midnight / 86400
        logger.debug(f"Converted datetime {dt} to SAS float: {sas_datetime}")
        return sas_datetime

    elif isinstance(dt, datetime.time):
        # For time objects, convert to SAS date representation (time-only)
        seconds_since_midnight = (
            dt.hour * 3600 +
            dt.minute * 60 +
            dt.second +
            dt.microsecond / 1e6
        )
        sas_time = seconds_since_midnight / 86400
        logger.debug(f"Converted time {dt} to SAS float: {sas_time}")
        return sas_time

    else:
        raise TypeError(
            f"Expected datetime.date, datetime.datetime, or datetime.time, "
            f"got {type(dt).__name__}"
        )


def infer_data_type(value):
    """
    Infer the Dataset-JSON data type from a Python value.

    Args:
        value: Any Python value

    Returns:
        str: One of 'string', 'integer', 'double', or None
    """
    if isinstance(value, str):
        return "string"
    elif isinstance(value, bool):
        return "string"  # Booleans treated as strings in SAS
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return "double"  # SAS dates are stored as numbers
    else:
        return None


def normalize_column_name(name):
    """
    Normalize column name for comparison.

    Args:
        name (str): Column name

    Returns:
        str: Normalized column name (uppercase, stripped)
    """
    return name.strip().upper()


def match_column_names(source_columns, metadata_columns):
    """
    Match source dataset columns with metadata columns.

    Uses case-insensitive matching and returns a mapping.

    Args:
        source_columns (list): List of column names from source dataset
        metadata_columns (list): List of column names from metadata

    Returns:
        dict: Mapping of source column names to metadata column names

    Raises:
        ValueError: If columns cannot be matched
    """
    normalized_source = {normalize_column_name(col): col for col in source_columns}
    normalized_metadata = {normalize_column_name(col): col for col in metadata_columns}

    if set(normalized_source.keys()) != set(normalized_metadata.keys()):
        missing_in_metadata = set(normalized_source.keys()) - set(normalized_metadata.keys())
        missing_in_source = set(normalized_metadata.keys()) - set(normalized_source.keys())

        error_parts = []
        if missing_in_metadata:
            error_parts.append(
                f"Columns in source but not in metadata: {missing_in_metadata}"
            )
        if missing_in_source:
            error_parts.append(
                f"Columns in metadata but not in source: {missing_in_source}"
            )

        raise ValueError(
            "Column names mismatch between source and metadata. " +
            " ".join(error_parts)
        )

    # Create mapping from source column names to metadata column names
    mapping = {}
    for norm_name, source_name in normalized_source.items():
        metadata_name = normalized_metadata[norm_name]
        mapping[source_name] = metadata_name

    return mapping


def get_package_resource_path(resource_name):
    """
    Get the path to a package resource file.

    Args:
        resource_name (str): Name of the resource (e.g., 'schemas/dataset.schema.json')

    Returns:
        str: Absolute path to the resource
    """
    import os
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(package_dir, resource_name)
