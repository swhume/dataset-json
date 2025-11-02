"""
Unit tests for dsjconvert.xpt_writer module.

Tests XPT writer functionality and Dataset-JSON to DataFrame conversion.
"""

import pytest
import pandas as pd
import pyreadstat
import datetime
from pathlib import Path

from dsjconvert.xpt_writer import (
    XPTWriter,
    convert_dataset_json_to_dataframe,
    integer_to_datetime,
    write_dataset_json_to_xpt
)
from dsjconvert.exceptions import DatasetConversionError


class TestIntegerToDatetime:
    """Test suite for integer_to_datetime function."""

    def test_convert_date_epoch(self):
        """Test converting SAS date 0 (1960-01-01)."""
        result = integer_to_datetime(0, 'date')
        assert result == datetime.date(1960, 1, 1)

    def test_convert_date_positive(self):
        """Test converting positive SAS date."""
        result = integer_to_datetime(1, 'date')
        assert result == datetime.date(1960, 1, 2)

        result = integer_to_datetime(366, 'date')
        assert result == datetime.date(1961, 1, 1)

    def test_convert_date_negative(self):
        """Test converting negative SAS date (before 1960)."""
        result = integer_to_datetime(-1, 'date')
        assert result == datetime.date(1959, 12, 31)

    def test_convert_datetime_epoch(self):
        """Test converting SAS datetime 0 (1960-01-01 00:00:00)."""
        result = integer_to_datetime(0, 'datetime')
        assert result == datetime.datetime(1960, 1, 1, 0, 0, 0)

    def test_convert_datetime_with_time(self):
        """Test converting SAS datetime with fractional day."""
        # 0.5 = 12:00:00 (noon)
        result = integer_to_datetime(0.5, 'datetime')
        assert result == datetime.datetime(1960, 1, 1, 12, 0, 0)

        # 1.25 = 1960-01-02 06:00:00
        result = integer_to_datetime(1.25, 'datetime')
        assert result == datetime.datetime(1960, 1, 2, 6, 0, 0)

    def test_convert_time_midnight(self):
        """Test converting SAS time 0 (midnight)."""
        result = integer_to_datetime(0, 'time')
        assert result == datetime.time(0, 0, 0)

    def test_convert_time_noon(self):
        """Test converting SAS time 0.5 (noon)."""
        result = integer_to_datetime(0.5, 'time')
        assert result == datetime.time(12, 0, 0)

    def test_convert_time_evening(self):
        """Test converting SAS time 0.75 (18:00)."""
        result = integer_to_datetime(0.75, 'time')
        assert result == datetime.time(18, 0, 0)

    def test_convert_null_value(self):
        """Test converting null/None values."""
        assert integer_to_datetime(None, 'date') is None
        assert integer_to_datetime(None, 'datetime') is None
        assert integer_to_datetime(None, 'time') is None

    def test_convert_non_datetime_type(self):
        """Test that non-datetime types are returned as-is."""
        result = integer_to_datetime(123, 'string')
        assert result == 123

        result = integer_to_datetime(45.6, 'double')
        assert result == 45.6


class TestConvertDatasetJSONToDataFrame:
    """Test suite for convert_dataset_json_to_dataframe function."""

    def test_convert_basic_dataset(self, sample_metadata, sample_rows):
        """Test converting basic Dataset-JSON to DataFrame."""
        df = convert_dataset_json_to_dataframe(sample_metadata, sample_rows)

        assert len(df) == 3
        assert len(df.columns) == 3
        assert list(df.columns) == ['STUDYID', 'SUBJID', 'AGE']
        assert df.iloc[0, 0] == 'STUDY001'
        assert df.iloc[0, 2] == 25

    def test_convert_empty_dataset(self, sample_metadata):
        """Test converting Dataset-JSON with no rows."""
        df = convert_dataset_json_to_dataframe(sample_metadata, [])

        assert len(df) == 0
        assert len(df.columns) == 3
        assert list(df.columns) == ['STUDYID', 'SUBJID', 'AGE']

    def test_convert_missing_columns(self):
        """Test converting Dataset-JSON without columns field."""
        metadata = {"name": "TEST"}
        with pytest.raises(ValueError) as exc_info:
            convert_dataset_json_to_dataframe(metadata, [])

        assert "must contain 'columns' field" in str(exc_info.value)

    def test_convert_column_missing_name(self):
        """Test converting with column missing name field."""
        metadata = {
            "name": "TEST",
            "columns": [
                {"label": "Column 1", "dataType": "string"}
            ]
        }
        with pytest.raises(ValueError) as exc_info:
            convert_dataset_json_to_dataframe(metadata, [])

        assert "must have a 'name' field" in str(exc_info.value)

    def test_convert_mismatched_row_length(self, sample_metadata):
        """Test converting with rows that don't match column count."""
        rows = [
            ["VAL1", "VAL2"]  # Only 2 values, but metadata has 3 columns
        ]

        with pytest.raises(ValueError) as exc_info:
            convert_dataset_json_to_dataframe(sample_metadata, rows)

        assert "has 2 values, expected 3" in str(exc_info.value)


class TestXPTWriter:
    """Test suite for XPTWriter class."""

    def test_write_basic_dataset(self, temp_dir, sample_metadata):
        """Test writing a basic DataFrame to XPT."""
        # Create test DataFrame
        df = pd.DataFrame({
            'STUDYID': ['STUDY001', 'STUDY001'],
            'SUBJID': ['001', '002'],
            'AGE': [25, 30]
        })

        # Write to XPT
        output_path = temp_dir / "test.xpt"
        writer = XPTWriter()
        writer.write(str(output_path), df, sample_metadata)

        # Verify file was created
        assert output_path.exists()

        # Read back and verify
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert len(df_read) == 2
        assert len(df_read.columns) == 3
        assert meta.table_name == 'TESTDATA'

    def test_write_with_custom_table_name(self, temp_dir, sample_metadata):
        """Test writing with custom table name."""
        df = pd.DataFrame({'COL1': [1, 2, 3]})
        sample_metadata['columns'] = [{'name': 'COL1', 'label': 'Column 1'}]

        output_path = temp_dir / "custom.xpt"
        writer = XPTWriter()
        writer.write(
            str(output_path),
            df,
            sample_metadata,
            table_name='CUSTOM'
        )

        # Verify
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert meta.table_name == 'CUSTOM'

    def test_write_with_column_labels(self, temp_dir):
        """Test that column labels are preserved."""
        df = pd.DataFrame({
            'VAR1': ['A', 'B'],
            'VAR2': [1, 2]
        })

        metadata = {
            'name': 'TEST',
            'label': 'Test Dataset',
            'columns': [
                {'name': 'VAR1', 'label': 'Variable 1', 'dataType': 'string'},
                {'name': 'VAR2', 'label': 'Variable 2', 'dataType': 'integer'}
            ]
        }

        output_path = temp_dir / "labels.xpt"
        writer = XPTWriter()
        writer.write(str(output_path), df, metadata)

        # Verify labels
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert meta.column_labels[0] == 'Variable 1'
        assert meta.column_labels[1] == 'Variable 2'

    # def test_write_empty_dataset(self, temp_dir, sample_metadata):
    #     """Test writing an empty DataFrame."""
    #     df = pd.DataFrame(columns=['STUDYID', 'SUBJID', 'AGE'])
    #
    #     output_path = temp_dir / "empty.xpt"
    #     writer = XPTWriter()
    #     writer.write(str(output_path), df, sample_metadata)
    #
    #     # Verify
    #     assert output_path.exists()
    #     df_read, meta = pyreadstat.read_xport(str(output_path))
    #     assert len(df_read) == 0
    #     assert len(df_read.columns) == 3


class TestWriteDatasetJSONToXPT:
    """Test suite for write_dataset_json_to_xpt convenience function."""

    def test_write_json_to_xpt(self, temp_dir, sample_metadata, sample_rows):
        """Test end-to-end JSON to XPT conversion."""
        import json

        # Create JSON file
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "input.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        # Convert to XPT
        output_path = temp_dir / "output.xpt"
        write_dataset_json_to_xpt(str(json_file), str(output_path))

        # Verify
        assert output_path.exists()
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert len(df_read) == 3
        assert meta.table_name == 'TESTDATA'

    def test_write_ndjson_to_xpt(self, temp_dir, sample_metadata, sample_rows):
        """Test end-to-end NDJSON to XPT conversion."""
        import json

        # Create NDJSON file
        ndjson_file = temp_dir / "input.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            for row in sample_rows:
                f.write(json.dumps(row) + '\n')

        # Convert to XPT
        output_path = temp_dir / "output.xpt"
        write_dataset_json_to_xpt(str(ndjson_file), str(output_path))

        # Verify
        assert output_path.exists()
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert len(df_read) == 3
        assert meta.table_name == 'TESTDATA'

    def test_write_with_auto_format_detection(self, temp_dir, sample_metadata, sample_rows):
        """Test that format is auto-detected from file extension."""
        import json

        # Create JSON file without specifying format
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "auto.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        output_path = temp_dir / "auto.xpt"
        write_dataset_json_to_xpt(str(json_file), str(output_path), input_format=None)

        # Verify it worked
        assert output_path.exists()
        df_read, meta = pyreadstat.read_xport(str(output_path))
        assert len(df_read) == 3
