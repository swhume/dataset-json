"""
Unit tests for dsjconvert.reverse_converter module.

Tests reverse conversion from Dataset-JSON to XPT format.
"""

import pytest
import json
import pyreadstat
from pathlib import Path

from dsjconvert.reverse_converter import (
    DatasetJSONToXPTConverter,
    convert_json_to_xpt
)
from dsjconvert.exceptions import DatasetReadError, DatasetConversionError


class TestDatasetJSONToXPTConverterInit:
    """Test suite for DatasetJSONToXPTConverter initialization."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        converter = DatasetJSONToXPTConverter()

        assert converter.input_format == 'ndjson'
        assert converter.validator is not None
        assert converter.reader is not None
        assert converter.writer is not None

    def test_init_with_json_format(self):
        """Test initialization with JSON input format."""
        converter = DatasetJSONToXPTConverter(input_format='json')

        assert converter.input_format == 'json'

    def test_init_with_skip_validation(self):
        """Test initialization with skip_validation."""
        converter = DatasetJSONToXPTConverter(skip_validation=True)

        assert converter.validator.skip_validation is True


class TestExtractDatasetName:
    """Test suite for _extract_dataset_name method."""

    def test_extract_from_json_file(self):
        """Test extracting dataset name from .json file."""
        converter = DatasetJSONToXPTConverter()

        name = converter._extract_dataset_name("dm.json")

        assert name == "DM"

    def test_extract_from_ndjson_file(self):
        """Test extracting dataset name from .ndjson file."""
        converter = DatasetJSONToXPTConverter()

        name = converter._extract_dataset_name("ae.ndjson")

        assert name == "AE"

    def test_extract_from_path(self):
        """Test extracting dataset name from full path."""
        converter = DatasetJSONToXPTConverter()

        name = converter._extract_dataset_name("/path/to/datasets/vs.ndjson")

        assert name == "VS"

    def test_extract_converts_to_uppercase(self):
        """Test that dataset name is converted to uppercase."""
        converter = DatasetJSONToXPTConverter()

        name = converter._extract_dataset_name("study_data.json")

        assert name == "STUDY_DATA"


class TestConvertDataset:
    """Test suite for convert_dataset method."""

    def test_convert_json_dataset(self, temp_dir, sample_metadata, sample_rows):
        """Test converting a JSON file to XPT."""
        # Create input JSON file
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "testdata.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        # Convert
        converter = DatasetJSONToXPTConverter(input_format='json')
        output_path = converter.convert_dataset(
            str(json_file),
            str(temp_dir)
        )

        # Verify output file exists and has correct name
        assert Path(output_path).exists()
        assert output_path.endswith('TESTDATA.xpt')

        # Read back and verify content
        df, meta = pyreadstat.read_xport(output_path)
        assert len(df) == 3
        assert len(df.columns) == 3
        assert meta.table_name == 'TESTDATA'

    def test_convert_ndjson_dataset(self, temp_dir, sample_metadata, sample_rows):
        """Test converting an NDJSON file to XPT."""
        # Create input NDJSON file
        ndjson_file = temp_dir / "testdata.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            for row in sample_rows:
                f.write(json.dumps(row) + '\n')

        # Convert
        converter = DatasetJSONToXPTConverter(input_format='ndjson')
        output_path = converter.convert_dataset(
            str(ndjson_file),
            str(temp_dir)
        )

        # Verify
        assert Path(output_path).exists()
        df, meta = pyreadstat.read_xport(output_path)
        assert len(df) == 3
        assert meta.table_name == 'TESTDATA'

    def test_convert_with_explicit_dataset_name(self, temp_dir, sample_metadata, sample_rows):
        """Test conversion with explicitly specified dataset name."""
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "input.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        converter = DatasetJSONToXPTConverter(input_format='json')
        output_path = converter.convert_dataset(
            str(json_file),
            str(temp_dir),
            dataset_name='CUSTOM'
        )

        # Verify custom name is used
        assert output_path.endswith('CUSTOM.xpt')

    def test_convert_empty_dataset(self, temp_dir, sample_metadata):
        """Test converting an empty dataset."""
        dataset = sample_metadata.copy()
        dataset['rows'] = []
        json_file = temp_dir / "empty.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        converter = DatasetJSONToXPTConverter(input_format='json')
        output_path = converter.convert_dataset(
            str(json_file),
            str(temp_dir)
        )

        # Verify: empty datasets are skipped
        assert output_path is None
        expected_path = Path(temp_dir) / "EMPTY.xpt"
        assert not expected_path.exists()

    def test_convert_nonexistent_file(self, temp_dir):
        """Test converting a file that doesn't exist."""
        converter = DatasetJSONToXPTConverter(input_format='json')

        with pytest.raises(DatasetReadError):
            converter.convert_dataset(
                "/nonexistent/file.json",
                str(temp_dir)
            )

    def test_convert_invalid_json(self, temp_dir):
        """Test converting a file with invalid JSON."""
        json_file = temp_dir / "invalid.json"
        with open(json_file, 'w') as f:
            f.write("{ invalid json }")

        converter = DatasetJSONToXPTConverter(input_format='json')

        with pytest.raises(DatasetReadError):
            converter.convert_dataset(
                str(json_file),
                str(temp_dir)
            )


class TestConvertJSONToXPT:
    """Test suite for convert_json_to_xpt convenience function."""

    def test_convert_with_explicit_format(self, temp_dir, sample_metadata, sample_rows):
        """Test conversion with explicit format specification."""
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        output_path = convert_json_to_xpt(
            str(json_file),
            str(temp_dir),
            input_format='json'
        )

        assert Path(output_path).exists()
        df, _ = pyreadstat.read_xport(output_path)
        assert len(df) == 3

    def test_convert_with_auto_detect(self, temp_dir, sample_metadata, sample_rows):
        """Test conversion with auto-detected format."""
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        output_path = convert_json_to_xpt(
            str(json_file),
            str(temp_dir)
        )

        assert Path(output_path).exists()
        df, _ = pyreadstat.read_xport(output_path)
        assert len(df) == 3

    def test_convert_with_skip_validation(self, temp_dir, sample_metadata, sample_rows):
        """Test conversion with validation skipped."""
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows
        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        output_path = convert_json_to_xpt(
            str(json_file),
            str(temp_dir),
            skip_validation=True
        )

        assert Path(output_path).exists()
