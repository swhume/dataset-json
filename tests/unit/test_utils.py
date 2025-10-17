"""
Unit tests for dsjconvert.utils module.

Tests utility functions for datetime conversion, type inference,
and column name matching.
"""

import pytest
import datetime
from dsjconvert.utils import (
    datetime_to_integer,
    infer_data_type,
    normalize_column_name,
    match_column_names,
    get_package_resource_path
)


class TestDatetimeToInteger:
    """Test suite for datetime_to_integer function."""

    def test_date_epoch(self):
        """Test that 1960-01-01 converts to 0 (SAS epoch)."""
        date = datetime.date(1960, 1, 1)
        result = datetime_to_integer(date)
        assert result == 0

    def test_date_after_epoch(self):
        """Test date after epoch."""
        date = datetime.date(1960, 1, 2)
        result = datetime_to_integer(date)
        assert result == 1

    def test_date_before_epoch(self):
        """Test date before epoch (negative value)."""
        date = datetime.date(1959, 12, 31)
        result = datetime_to_integer(date)
        assert result == -1

    def test_date_year_2000(self):
        """Test date conversion for Y2K."""
        date = datetime.date(2000, 1, 1)
        # Days from 1960-01-01 to 2000-01-01
        expected = (date - datetime.date(1960, 1, 1)).days
        result = datetime_to_integer(date)
        assert result == expected
        assert result == 14610  # Verified value

    def test_datetime_epoch_midnight(self):
        """Test datetime at epoch midnight."""
        dt = datetime.datetime(1960, 1, 1, 0, 0, 0)
        result = datetime_to_integer(dt)
        assert result == 0.0

    def test_datetime_epoch_noon(self):
        """Test datetime at epoch noon."""
        dt = datetime.datetime(1960, 1, 1, 12, 0, 0)
        result = datetime_to_integer(dt)
        # 12 hours = 0.5 days
        assert result == 0.5

    def test_datetime_with_seconds(self):
        """Test datetime with hours, minutes, seconds."""
        dt = datetime.datetime(1960, 1, 2, 13, 30, 45)
        # 1 day + (13.5125 hours / 24)
        seconds_since_midnight = 13 * 3600 + 30 * 60 + 45
        expected = 1 + (seconds_since_midnight / 86400)
        result = datetime_to_integer(dt)
        assert abs(result - expected) < 0.000001  # Float comparison

    def test_datetime_with_microseconds(self):
        """Test datetime with microseconds precision."""
        dt = datetime.datetime(1960, 1, 1, 0, 0, 0, 500000)  # 0.5 seconds
        result = datetime_to_integer(dt)
        expected = 0.5 / 86400  # 0.5 seconds as fraction of day
        assert abs(result - expected) < 0.0000001

    def test_time_midnight(self):
        """Test time at midnight."""
        time = datetime.time(0, 0, 0)
        result = datetime_to_integer(time)
        assert result == 0.0

    def test_time_noon(self):
        """Test time at noon."""
        time = datetime.time(12, 0, 0)
        result = datetime_to_integer(time)
        assert result == 0.5

    def test_time_end_of_day(self):
        """Test time at 23:59:59."""
        time = datetime.time(23, 59, 59)
        seconds = 23 * 3600 + 59 * 60 + 59
        expected = seconds / 86400
        result = datetime_to_integer(time)
        assert abs(result - expected) < 0.000001

    def test_leap_year_date(self):
        """Test date in leap year."""
        date = datetime.date(2000, 2, 29)  # Leap day
        expected = (date - datetime.date(1960, 1, 1)).days
        result = datetime_to_integer(date)
        assert result == expected

    def test_invalid_type_raises_error(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError):
            datetime_to_integer("not a datetime")

    def test_invalid_number_raises_error(self):
        """Test that number raises TypeError."""
        with pytest.raises(TypeError):
            datetime_to_integer(12345)


class TestInferDataType:
    """Test suite for infer_data_type function."""

    def test_infer_string(self):
        """Test string type inference."""
        assert infer_data_type("hello") == "string"
        assert infer_data_type("") == "string"

    def test_infer_integer(self):
        """Test integer type inference."""
        assert infer_data_type(42) == "integer"
        assert infer_data_type(0) == "integer"
        assert infer_data_type(-10) == "integer"

    def test_infer_float(self):
        """Test float/double type inference."""
        assert infer_data_type(3.14) == "double"
        assert infer_data_type(0.0) == "double"
        assert infer_data_type(-2.5) == "double"

    def test_infer_boolean(self):
        """Test boolean type inference (treated as string in SAS)."""
        assert infer_data_type(True) == "string"
        assert infer_data_type(False) == "string"

    def test_infer_date(self):
        """Test date type inference (stored as double in SAS)."""
        assert infer_data_type(datetime.date(2024, 1, 1)) == "double"

    def test_infer_datetime(self):
        """Test datetime type inference (stored as double in SAS)."""
        assert infer_data_type(datetime.datetime(2024, 1, 1, 12, 0)) == "double"

    def test_infer_time(self):
        """Test time type inference (stored as double in SAS)."""
        assert infer_data_type(datetime.time(12, 30)) == "double"

    def test_infer_none(self):
        """Test None value returns None."""
        assert infer_data_type(None) is None

    def test_infer_unknown_type(self):
        """Test unknown type returns None."""
        assert infer_data_type([1, 2, 3]) is None
        assert infer_data_type({"key": "value"}) is None


class TestNormalizeColumnName:
    """Test suite for normalize_column_name function."""

    def test_normalize_uppercase(self):
        """Test normalization converts to uppercase."""
        assert normalize_column_name("studyid") == "STUDYID"
        assert normalize_column_name("STUDYID") == "STUDYID"

    def test_normalize_strips_whitespace(self):
        """Test normalization strips whitespace."""
        assert normalize_column_name("  STUDYID  ") == "STUDYID"
        assert normalize_column_name("\tSTUDYID\n") == "STUDYID"

    def test_normalize_mixed_case(self):
        """Test mixed case normalization."""
        assert normalize_column_name("StudyId") == "STUDYID"
        assert normalize_column_name("sTuDyId") == "STUDYID"

    def test_normalize_empty_string(self):
        """Test empty string normalization."""
        assert normalize_column_name("") == ""
        assert normalize_column_name("   ") == ""


class TestMatchColumnNames:
    """Test suite for match_column_names function."""

    def test_exact_match(self):
        """Test exact column name match."""
        source = ["STUDYID", "SUBJID", "AGE"]
        metadata = ["STUDYID", "SUBJID", "AGE"]
        result = match_column_names(source, metadata)

        assert result == {
            "STUDYID": "STUDYID",
            "SUBJID": "SUBJID",
            "AGE": "AGE"
        }

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        source = ["studyid", "subjid", "age"]
        metadata = ["STUDYID", "SUBJID", "AGE"]
        result = match_column_names(source, metadata)

        assert result == {
            "studyid": "STUDYID",
            "subjid": "SUBJID",
            "age": "AGE"
        }

    def test_mixed_case_match(self):
        """Test mixed case matching."""
        source = ["StudyID", "SubjID", "Age"]
        metadata = ["STUDYID", "SUBJID", "AGE"]
        result = match_column_names(source, metadata)

        assert result == {
            "StudyID": "STUDYID",
            "SubjID": "SUBJID",
            "Age": "AGE"
        }

    def test_whitespace_handling(self):
        """Test whitespace is stripped in matching."""
        source = ["  STUDYID  ", "SUBJID", "AGE"]
        metadata = ["STUDYID", "SUBJID", "AGE"]
        result = match_column_names(source, metadata)

        assert result == {
            "  STUDYID  ": "STUDYID",
            "SUBJID": "SUBJID",
            "AGE": "AGE"
        }

    def test_missing_in_metadata(self):
        """Test ValueError when column missing in metadata."""
        source = ["STUDYID", "SUBJID", "EXTRACOLUMN"]
        metadata = ["STUDYID", "SUBJID"]

        with pytest.raises(ValueError) as exc_info:
            match_column_names(source, metadata)

        assert "EXTRACOLUMN" in str(exc_info.value)
        assert "not in metadata" in str(exc_info.value).lower()

    def test_missing_in_source(self):
        """Test ValueError when column missing in source."""
        source = ["STUDYID", "SUBJID"]
        metadata = ["STUDYID", "SUBJID", "AGE"]

        with pytest.raises(ValueError) as exc_info:
            match_column_names(source, metadata)

        assert "AGE" in str(exc_info.value)
        assert "not in source" in str(exc_info.value).lower()

    def test_empty_lists(self):
        """Test empty column lists."""
        result = match_column_names([], [])
        assert result == {}

    def test_order_independence(self):
        """Test that column order doesn't matter."""
        source = ["AGE", "STUDYID", "SUBJID"]
        metadata = ["STUDYID", "SUBJID", "AGE"]
        result = match_column_names(source, metadata)

        assert len(result) == 3
        assert all(k in result for k in source)


class TestGetPackageResourcePath:
    """Test suite for get_package_resource_path function."""

    def test_schemas_path(self):
        """Test getting schemas directory path."""
        path = get_package_resource_path("schemas")
        assert "dsjconvert" in str(path)
        assert "schemas" in str(path)

    def test_schema_file_path(self):
        """Test getting specific schema file path."""
        path = get_package_resource_path("schemas/dataset.schema.json")
        assert "dsjconvert" in str(path)
        assert "dataset.schema.json" in str(path)

    def test_returns_absolute_path(self):
        """Test that returned path is absolute."""
        import os
        path = get_package_resource_path("schemas")
        assert os.path.isabs(path)
