"""
Unit tests for dsjconvert.converter module.

Tests dataset conversion logic for both XPT and SAS7BDAT formats.
"""

import pytest
import pandas as pd
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from dsjconvert.converter import (
    DatasetConverter,
    XPTConverter,
    SAS7BDATConverter
)
from dsjconvert.metadata import MetadataExtractor
from dsjconvert.exceptions import DatasetReadError, DatasetConversionError


class TestDatasetConverterInit:
    """Test suite for DatasetConverter initialization."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        converter = XPTConverter()  # Using concrete subclass

        assert converter.metadata_extractor is None
        assert converter.output_format == 'ndjson'
        assert converter.validator is not None
        assert converter.writer is not None

    def test_init_with_metadata_extractor(self, minimal_define_xml):
        """Test initialization with metadata extractor."""
        extractor = MetadataExtractor(minimal_define_xml)
        converter = XPTConverter(metadata_extractor=extractor)

        assert converter.metadata_extractor is extractor

    def test_init_with_json_format(self):
        """Test initialization with JSON output format."""
        converter = XPTConverter(output_format='json')

        assert converter.output_format == 'json'

    def test_init_with_skip_validation(self):
        """Test initialization with skip_validation."""
        converter = XPTConverter(skip_validation=True)

        assert converter.validator.skip_validation is True

    def test_init_creates_appropriate_writer(self):
        """Test that correct writer is created for format."""
        from dsjconvert.writers import JSONWriter, NDJSONWriter

        json_converter = XPTConverter(output_format='json')
        ndjson_converter = XPTConverter(output_format='ndjson')

        assert isinstance(json_converter.writer, JSONWriter)
        assert isinstance(ndjson_converter.writer, NDJSONWriter)


class TestExtractDatasetName:
    """Test suite for _extract_dataset_name method."""

    def test_extract_from_simple_filename(self):
        """Test extracting dataset name from simple filename."""
        converter = XPTConverter()

        name = converter._extract_dataset_name("dm.xpt")

        assert name == "DM"

    def test_extract_from_path(self):
        """Test extracting dataset name from full path."""
        converter = XPTConverter()

        name = converter._extract_dataset_name("/path/to/datasets/ae.xpt")

        assert name == "AE"

    def test_extract_converts_to_uppercase(self):
        """Test that dataset name is converted to uppercase."""
        converter = XPTConverter()

        name = converter._extract_dataset_name("study_data.xpt")

        assert name == "STUDY_DATA"

    def test_extract_handles_multiple_dots(self):
        """Test handling filename with multiple dots."""
        converter = XPTConverter()

        name = converter._extract_dataset_name("my.dataset.xpt")

        assert name == "MY.DATASET"

    def test_extract_different_extensions(self):
        """Test extracting name from different file extensions."""
        converter = XPTConverter()

        assert converter._extract_dataset_name("data.sas7bdat") == "DATA"
        assert converter._extract_dataset_name("test.csv") == "TEST"


class TestInferColumns:
    """Test suite for _infer_columns method."""

    def test_infer_columns_basic(self, sample_dataframe):
        """Test basic column inference from DataFrame."""
        converter = XPTConverter()
        mock_meta = MagicMock()
        mock_meta.column_labels = None

        columns = converter._infer_columns(sample_dataframe, mock_meta)

        assert len(columns) == len(sample_dataframe.columns)
        assert all('name' in col for col in columns)
        assert all('dataType' in col for col in columns)
        assert all('itemOID' in col for col in columns)

    def test_infer_columns_with_labels(self, sample_dataframe):
        """Test column inference with labels from metadata."""
        converter = XPTConverter()
        mock_meta = MagicMock()
        mock_meta.column_labels = ['Study ID', 'Subject ID', 'Age', 'Weight', 'Visit Date']

        columns = converter._infer_columns(sample_dataframe, mock_meta)

        assert columns[0]['label'] == 'Study ID'
        assert columns[1]['label'] == 'Subject ID'

    def test_infer_columns_with_metadata_extractor(self, sample_dataframe, minimal_define_xml):
        """Test column inference using metadata extractor."""
        extractor = MetadataExtractor(minimal_define_xml)
        converter = XPTConverter(metadata_extractor=extractor)
        mock_meta = MagicMock()
        mock_meta.column_labels = None

        columns = converter._infer_columns(sample_dataframe, mock_meta)

        assert len(columns) > 0
        assert all('name' in col for col in columns)

    def test_infer_columns_detects_types(self):
        """Test that column types are inferred when possible."""
        df = pd.DataFrame({
            'STRING_COL': ['A', 'B', 'C'],
            'FLOAT_COL': [1.1, 2.2, 3.3]
        })
        converter = XPTConverter()
        mock_meta = MagicMock()
        mock_meta.column_labels = None

        columns = converter._infer_columns(df, mock_meta)

        types = {col['name']: col['dataType'] for col in columns}
        # String values are detected
        assert types['STRING_COL'] == 'string'
        # Float values are detected
        assert types['FLOAT_COL'] == 'double'
        # All columns have a dataType (may be default 'string' for unrecognized types)
        assert all(col.get('dataType') is not None for col in columns)


class TestConvertValue:
    """Test suite for _convert_value method."""

    def test_convert_string_value(self):
        """Test converting string values."""
        converter = XPTConverter()

        result = converter._convert_value("test", "string")

        assert result == "test"

    def test_convert_integer_value(self):
        """Test converting integer values."""
        converter = XPTConverter()

        result = converter._convert_value(42, "integer")

        assert result == 42

    def test_convert_float_value(self):
        """Test converting float values."""
        converter = XPTConverter()

        result = converter._convert_value(3.14, "double")

        assert result == 3.14

    def test_convert_na_value(self):
        """Test converting NA/null values."""
        converter = XPTConverter()

        result = converter._convert_value(pd.NA, "string")

        assert result is None

    def test_convert_empty_string_to_integer(self):
        """Test converting empty string for integer type."""
        converter = XPTConverter()

        result = converter._convert_value("", "integer")

        assert result is None

    def test_convert_datetime_value(self):
        """Test converting datetime values."""
        converter = XPTConverter()
        dt = datetime.datetime(1960, 1, 2, 12, 0, 0)

        result = converter._convert_value(dt, "double")

        # Should be 1.5 days from epoch (1 day + 12 hours)
        assert result == 1.5

    def test_convert_date_value(self):
        """Test converting date values."""
        converter = XPTConverter()
        date = datetime.date(1960, 1, 2)

        result = converter._convert_value(date, "double")

        # Should be 1 day from epoch
        assert result == 1

    def test_convert_time_value(self):
        """Test converting time values."""
        converter = XPTConverter()
        time = datetime.time(12, 0, 0)

        result = converter._convert_value(time, "double")

        # Should be 0.5 (12 hours = half a day)
        assert result == 0.5

    def test_convert_none_value(self):
        """Test converting None values."""
        converter = XPTConverter()

        result = converter._convert_value(None, "string")

        assert result is None


class TestConvertRow:
    """Test suite for _convert_row method."""

    def test_convert_simple_row(self):
        """Test converting a simple row."""
        converter = XPTConverter()
        row = pd.Series({'COL1': 'A', 'COL2': 42, 'COL3': 3.14})
        column_mapping = {'COL1': 'COL1', 'COL2': 'COL2', 'COL3': 'COL3'}
        column_types = {'COL1': 'string', 'COL2': 'integer', 'COL3': 'double'}

        result = converter._convert_row(row, column_mapping, column_types)

        assert result == ['A', 42, 3.14]

    def test_convert_row_with_nulls(self):
        """Test converting row with null values."""
        converter = XPTConverter()
        row = pd.Series({'COL1': 'A', 'COL2': pd.NA, 'COL3': None})
        column_mapping = {'COL1': 'COL1', 'COL2': 'COL2', 'COL3': 'COL3'}
        column_types = {'COL1': 'string', 'COL2': 'integer', 'COL3': 'string'}

        result = converter._convert_row(row, column_mapping, column_types)

        assert result == ['A', None, None]

    def test_convert_row_with_column_mapping(self):
        """Test converting row with column name mapping."""
        converter = XPTConverter()
        row = pd.Series({'col1': 'A', 'col2': 42})
        column_mapping = {'col1': 'COL1', 'col2': 'COL2'}  # lowercase to uppercase
        column_types = {'COL1': 'string', 'COL2': 'integer'}

        result = converter._convert_row(row, column_mapping, column_types)

        assert result == ['A', 42]


class TestConvertRows:
    """Test suite for _convert_rows method."""

    def test_convert_empty_dataframe(self):
        """Test converting empty DataFrame."""
        converter = XPTConverter()
        df = pd.DataFrame()
        metadata = {'columns': []}

        rows = converter._convert_rows(df, metadata)

        assert rows == []

    def test_convert_dataframe_with_rows(self, sample_dataframe):
        """Test converting DataFrame with data."""
        converter = XPTConverter()
        metadata = {
            'columns': [
                {'name': 'STUDYID', 'dataType': 'string'},
                {'name': 'SUBJID', 'dataType': 'string'},
                {'name': 'AGE', 'dataType': 'integer'},
                {'name': 'WEIGHT', 'dataType': 'double'},
                {'name': 'VISITDATE', 'dataType': 'double'}
            ]
        }

        rows = converter._convert_rows(sample_dataframe, metadata)

        assert len(rows) == 3
        assert all(isinstance(row, list) for row in rows)
        assert len(rows[0]) == 5

    def test_convert_preserves_row_count(self):
        """Test that all rows are converted."""
        converter = XPTConverter()
        df = pd.DataFrame({
            'COL1': list(range(100)),
            'COL2': ['test'] * 100
        })
        metadata = {
            'columns': [
                {'name': 'COL1', 'dataType': 'integer'},
                {'name': 'COL2', 'dataType': 'string'}
            ]
        }

        rows = converter._convert_rows(df, metadata)

        assert len(rows) == 100


class TestXPTConverter:
    """Test suite for XPTConverter class."""

    def test_read_dataset_success(self, temp_dir):
        """Test successful reading of XPT file."""
        mock_df = pd.DataFrame({'COL1': [1, 2, 3]})
        mock_meta = MagicMock()
        mock_meta.number_rows = 3

        with patch('pyreadstat.read_xport', return_value=(mock_df, mock_meta)):
            converter = XPTConverter()
            df, meta = converter.read_dataset("test.xpt")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3
            assert meta.number_rows == 3

    def test_read_dataset_unicode_error(self):
        """Test handling of Unicode decode error."""
        with patch('pyreadstat.read_xport', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'error')):
            converter = XPTConverter()

            with pytest.raises(DatasetReadError) as exc_info:
                converter.read_dataset("test.xpt")

            assert "Unicode decode error" in str(exc_info.value)

    def test_read_dataset_general_error(self):
        """Test handling of general read error."""
        with patch('pyreadstat.read_xport', side_effect=Exception("File not found")):
            converter = XPTConverter()

            with pytest.raises(DatasetReadError) as exc_info:
                converter.read_dataset("test.xpt")

            assert exc_info.value.file_path == "test.xpt"


class TestSAS7BDATConverter:
    """Test suite for SAS7BDATConverter class."""

    def test_read_dataset_success(self):
        """Test successful reading of SAS7BDAT file."""
        mock_df = pd.DataFrame({'COL1': [1, 2, 3]})
        mock_meta = MagicMock()
        mock_meta.number_rows = 3

        with patch('pyreadstat.read_sas7bdat', return_value=(mock_df, mock_meta)):
            converter = SAS7BDATConverter()
            df, meta = converter.read_dataset("test.sas7bdat")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3

    def test_read_dataset_error(self):
        """Test handling of read error."""
        with patch('pyreadstat.read_sas7bdat', side_effect=Exception("Invalid file")):
            converter = SAS7BDATConverter()

            with pytest.raises(DatasetReadError) as exc_info:
                converter.read_dataset("test.sas7bdat")

            assert exc_info.value.file_path == "test.sas7bdat"


class TestConvertDataset:
    """Test suite for convert_dataset method (end-to-end conversion)."""

    def test_convert_dataset_minimal(self, temp_dir):
        """Test minimal dataset conversion."""
        # Create mock DataFrame and metadata
        mock_df = pd.DataFrame({
            'STUDYID': ['STUDY001'],
            'SUBJID': ['001'],
            'AGE': [25]
        })
        mock_meta = MagicMock()
        mock_meta.number_rows = 1
        mock_meta.column_labels = ['Study ID', 'Subject ID', 'Age']

        converter = XPTConverter()

        with patch.object(converter, 'read_dataset', return_value=(mock_df, mock_meta)):
            output_path = converter.convert_dataset(
                "test.xpt",
                str(temp_dir),
                dataset_name="TEST"
            )

            assert Path(output_path).exists()
            assert "TEST" in output_path
            assert output_path.endswith('.ndjson')

    def test_convert_dataset_infers_name(self, temp_dir):
        """Test that dataset name is inferred from filename."""
        mock_df = pd.DataFrame({'COL1': [1]})
        mock_meta = MagicMock()
        mock_meta.number_rows = 1
        mock_meta.column_labels = ['Column 1']

        converter = XPTConverter()

        with patch.object(converter, 'read_dataset', return_value=(mock_df, mock_meta)):
            output_path = converter.convert_dataset(
                "mydataset.xpt",
                str(temp_dir)
            )

            assert "MYDATASET" in output_path

    def test_convert_dataset_with_metadata_extractor(self, temp_dir, minimal_define_xml):
        """Test conversion with metadata extractor."""
        mock_df = pd.DataFrame({
            'STUDYID': ['STUDY001'],
            'SUBJID': ['001'],
            'AGE': [25]
        })
        mock_meta = MagicMock()
        mock_meta.number_rows = 1
        mock_meta.column_labels = None

        extractor = MetadataExtractor(minimal_define_xml)
        converter = XPTConverter(metadata_extractor=extractor)

        with patch.object(converter, 'read_dataset', return_value=(mock_df, mock_meta)):
            output_path = converter.convert_dataset(
                "testdata.xpt",
                str(temp_dir),
                dataset_name="TESTDATA"
            )

            assert Path(output_path).exists()

    def test_convert_dataset_json_format(self, temp_dir):
        """Test conversion to JSON format."""
        mock_df = pd.DataFrame({'COL1': [1]})
        mock_meta = MagicMock()
        mock_meta.number_rows = 1
        mock_meta.column_labels = None

        converter = XPTConverter(output_format='json')

        with patch.object(converter, 'read_dataset', return_value=(mock_df, mock_meta)):
            output_path = converter.convert_dataset(
                "test.xpt",
                str(temp_dir),
                dataset_name="TEST"
            )

            assert output_path.endswith('.json')

    def test_convert_dataset_handles_read_error(self, temp_dir):
        """Test that read errors are propagated."""
        converter = XPTConverter()

        with patch.object(converter, 'read_dataset', side_effect=DatasetReadError("test.xpt", "error")):
            with pytest.raises(DatasetReadError):
                converter.convert_dataset("test.xpt", str(temp_dir))

    def test_convert_dataset_handles_conversion_error(self, temp_dir):
        """Test that conversion errors are wrapped."""
        mock_df = pd.DataFrame({'COL1': [1]})
        mock_meta = MagicMock()

        converter = XPTConverter()

        with patch.object(converter, 'read_dataset', return_value=(mock_df, mock_meta)):
            with patch.object(converter, '_convert_rows', side_effect=Exception("Conversion failed")):
                with pytest.raises(DatasetConversionError) as exc_info:
                    converter.convert_dataset("test.xpt", str(temp_dir), dataset_name="TEST")

                assert exc_info.value.dataset_name == "TEST"


class TestExtractMetadata:
    """Test suite for _extract_metadata method."""

    def test_extract_with_metadata_extractor(self, minimal_define_xml):
        """Test metadata extraction with extractor."""
        extractor = MetadataExtractor(minimal_define_xml)
        converter = XPTConverter(metadata_extractor=extractor)

        mock_meta = MagicMock()
        mock_meta.number_rows = 100
        df = pd.DataFrame({'STUDYID': [1, 2, 3]})

        metadata = converter._extract_metadata("TESTDATA", mock_meta, df)

        assert metadata['name'] == 'TESTDATA'
        assert metadata['records'] == 100
        assert 'datasetJSONVersion' in metadata

    def test_extract_without_metadata_extractor(self):
        """Test metadata extraction without extractor."""
        converter = XPTConverter()

        mock_meta = MagicMock()
        mock_meta.number_rows = 50
        df = pd.DataFrame({'COL1': [1, 2, 3]})

        metadata = converter._extract_metadata("TEST", mock_meta, df)

        assert metadata['name'] == 'TEST'
        assert metadata['label'] == 'TEST'
        assert metadata['records'] == 50
        assert metadata['datasetJSONVersion'] == '1.1.0'

    def test_extract_infers_columns_when_empty(self):
        """Test that columns are inferred when metadata has no columns."""
        converter = XPTConverter()

        mock_meta = MagicMock()
        mock_meta.number_rows = 3
        mock_meta.column_labels = None
        df = pd.DataFrame({'COL1': [1, 2, 3], 'COL2': ['A', 'B', 'C']})

        metadata = converter._extract_metadata("TEST", mock_meta, df)

        assert len(metadata['columns']) == 2
        assert metadata['columns'][0]['name'] == 'COL1'
        assert metadata['columns'][1]['name'] == 'COL2'


class TestValidateDataset:
    """Test suite for _validate_dataset method."""

    def test_validate_json_format(self, sample_metadata, sample_rows):
        """Test validation for JSON format."""
        converter = XPTConverter(output_format='json')

        with patch.object(converter.validator, 'validate_json', return_value=True) as mock_validate:
            result = converter._validate_dataset(sample_metadata, sample_rows, "TEST")

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_ndjson_format(self, sample_metadata, sample_rows):
        """Test validation for NDJSON format."""
        converter = XPTConverter(output_format='ndjson')

        with patch.object(converter.validator, 'validate_ndjson', return_value=True) as mock_validate:
            result = converter._validate_dataset(sample_metadata, sample_rows, "TEST")

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_with_skip_validation(self):
        """Test that validation is skipped when configured."""
        converter = XPTConverter(skip_validation=True)

        # Should not raise error even with invalid data
        result = converter._validate_dataset({}, [], "TEST")

        assert result is True


class TestWriteOutput:
    """Test suite for _write_output method."""

    def test_write_output_ndjson(self, temp_dir, sample_metadata, sample_rows):
        """Test writing NDJSON output."""
        converter = XPTConverter(output_format='ndjson')

        output_path = converter._write_output(
            str(temp_dir),
            "TEST",
            sample_metadata,
            sample_rows
        )

        assert Path(output_path).exists()
        assert output_path.endswith('.ndjson')
        assert "TEST" in output_path

    def test_write_output_json(self, temp_dir, sample_metadata, sample_rows):
        """Test writing JSON output."""
        converter = XPTConverter(output_format='json')

        output_path = converter._write_output(
            str(temp_dir),
            "TEST",
            sample_metadata,
            sample_rows
        )

        assert Path(output_path).exists()
        assert output_path.endswith('.json')

    def test_write_output_creates_file(self, temp_dir):
        """Test that output file is created."""
        converter = XPTConverter()
        metadata = {
            "datasetJSONVersion": "1.1.0",
            "name": "TEST",
            "columns": []
        }

        output_path = converter._write_output(str(temp_dir), "TEST", metadata, [])

        output_file = Path(output_path)
        assert output_file.exists()
        assert output_file.stat().st_size > 0
