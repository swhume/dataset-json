"""
Unit tests for dsjconvert.readers module.

Tests Dataset-JSON reader functionality for both JSON and NDJSON formats.
"""

import pytest
import json
from pathlib import Path

from dsjconvert.readers import (
    JSONReader,
    NDJSONReader,
    ReaderFactory,
    read_dataset_json
)
from dsjconvert.exceptions import DatasetReadError, InvalidFormatError


class TestJSONReader:
    """Test suite for JSONReader class."""

    def test_read_valid_json(self, temp_dir, sample_metadata, sample_rows):
        """Test reading a valid JSON file."""
        # Create test JSON file
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows

        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        # Read with JSONReader
        reader = JSONReader()
        metadata, rows = reader.read(str(json_file))

        # Verify results
        assert metadata['name'] == 'TESTDATA'
        assert metadata['records'] == 3
        assert len(metadata['columns']) == 3
        assert rows == sample_rows
        assert 'rows' not in metadata  # rows should be extracted

    def test_read_empty_dataset(self, temp_dir, sample_metadata):
        """Test reading JSON with no rows."""
        dataset = sample_metadata.copy()
        dataset['rows'] = []

        json_file = temp_dir / "empty.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        reader = JSONReader()
        metadata, rows = reader.read(str(json_file))

        assert len(rows) == 0
        assert metadata['name'] == 'TESTDATA'

    def test_read_invalid_json(self, temp_dir):
        """Test reading file with invalid JSON."""
        json_file = temp_dir / "invalid.json"
        with open(json_file, 'w') as f:
            f.write("{ invalid json }")

        reader = JSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read(str(json_file))

        assert "Invalid JSON format" in str(exc_info.value)

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        reader = JSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read("/nonexistent/file.json")

        assert "Cannot read file" in str(exc_info.value)


class TestNDJSONReader:
    """Test suite for NDJSONReader class."""

    def test_read_valid_ndjson(self, temp_dir, sample_metadata, sample_rows):
        """Test reading a valid NDJSON file."""
        # Create test NDJSON file
        ndjson_file = temp_dir / "test.ndjson"
        with open(ndjson_file, 'w') as f:
            # Line 1: Metadata
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')

            # Lines 2-n: Rows
            for row in sample_rows:
                f.write(json.dumps(row) + '\n')

        # Read with NDJSONReader
        reader = NDJSONReader()
        metadata, rows = reader.read(str(ndjson_file))

        # Verify results
        assert metadata['name'] == 'TESTDATA'
        assert metadata['records'] == 3
        assert len(metadata['columns']) == 3
        assert rows == sample_rows

    def test_read_empty_dataset(self, temp_dir, sample_metadata):
        """Test reading NDJSON with only metadata."""
        ndjson_file = temp_dir / "empty.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')

        reader = NDJSONReader()
        metadata, rows = reader.read(str(ndjson_file))

        assert len(rows) == 0
        assert metadata['name'] == 'TESTDATA'

    def test_read_with_empty_lines(self, temp_dir, sample_metadata, sample_rows):
        """Test reading NDJSON with empty lines (should be skipped)."""
        ndjson_file = temp_dir / "with_empty.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            f.write('\n')  # Empty line
            f.write(json.dumps(sample_rows[0]) + '\n')
            f.write('\n')  # Another empty line
            f.write(json.dumps(sample_rows[1]) + '\n')

        reader = NDJSONReader()
        metadata, rows = reader.read(str(ndjson_file))

        assert len(rows) == 2
        assert rows[0] == sample_rows[0]
        assert rows[1] == sample_rows[1]

    def test_read_invalid_metadata_line(self, temp_dir):
        """Test reading NDJSON with invalid metadata line."""
        ndjson_file = temp_dir / "invalid_meta.ndjson"
        with open(ndjson_file, 'w') as f:
            f.write("{ invalid json }\n")

        reader = NDJSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read(str(ndjson_file))

        assert "Invalid JSON in metadata line" in str(exc_info.value)

    def test_read_invalid_row_line(self, temp_dir, sample_metadata):
        """Test reading NDJSON with invalid row line."""
        ndjson_file = temp_dir / "invalid_row.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            f.write("{ invalid json }\n")

        reader = NDJSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read(str(ndjson_file))

        assert "Invalid JSON in row data" in str(exc_info.value)

    def test_read_row_not_array(self, temp_dir, sample_metadata):
        """Test reading NDJSON where row is not an array."""
        ndjson_file = temp_dir / "row_not_array.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            f.write('{"not": "array"}\n')

        reader = NDJSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read(str(ndjson_file))

        assert "Row data must be a JSON array" in str(exc_info.value)

    def test_read_empty_file(self, temp_dir):
        """Test reading an empty NDJSON file."""
        ndjson_file = temp_dir / "empty_file.ndjson"
        ndjson_file.touch()

        reader = NDJSONReader()
        with pytest.raises(DatasetReadError) as exc_info:
            reader.read(str(ndjson_file))

        assert "File is empty" in str(exc_info.value)


class TestReaderFactory:
    """Test suite for ReaderFactory class."""

    def test_create_json_reader(self):
        """Test creating a JSON reader."""
        reader = ReaderFactory.create_reader('json')
        assert isinstance(reader, JSONReader)

    def test_create_ndjson_reader(self):
        """Test creating an NDJSON reader."""
        reader = ReaderFactory.create_reader('ndjson')
        assert isinstance(reader, NDJSONReader)

    def test_create_reader_case_insensitive(self):
        """Test that format names are case-insensitive."""
        reader1 = ReaderFactory.create_reader('JSON')
        reader2 = ReaderFactory.create_reader('NDJSON')

        assert isinstance(reader1, JSONReader)
        assert isinstance(reader2, NDJSONReader)

    def test_create_reader_invalid_format(self):
        """Test creating reader with invalid format."""
        with pytest.raises(InvalidFormatError) as exc_info:
            ReaderFactory.create_reader('xml')

        assert 'xml' in str(exc_info.value).lower()

    def test_create_reader_from_extension_json(self):
        """Test creating reader from .json extension."""
        reader = ReaderFactory.create_reader_from_extension('/path/to/file.json')
        assert isinstance(reader, JSONReader)

    def test_create_reader_from_extension_ndjson(self):
        """Test creating reader from .ndjson extension."""
        reader = ReaderFactory.create_reader_from_extension('/path/to/file.ndjson')
        assert isinstance(reader, NDJSONReader)

    def test_create_reader_from_extension_case_insensitive(self):
        """Test extension detection is case-insensitive."""
        reader1 = ReaderFactory.create_reader_from_extension('/path/to/file.JSON')
        reader2 = ReaderFactory.create_reader_from_extension('/path/to/file.NDJSON')

        assert isinstance(reader1, JSONReader)
        assert isinstance(reader2, NDJSONReader)

    def test_create_reader_from_extension_invalid(self):
        """Test creating reader from invalid extension."""
        with pytest.raises(InvalidFormatError) as exc_info:
            ReaderFactory.create_reader_from_extension('/path/to/file.xml')

        assert 'xml' in str(exc_info.value).lower()

    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = ReaderFactory.get_supported_formats()
        assert 'json' in formats
        assert 'ndjson' in formats


class TestReadDatasetJSON:
    """Test suite for read_dataset_json convenience function."""

    def test_read_with_explicit_format(self, temp_dir, sample_metadata, sample_rows):
        """Test reading with explicit format specification."""
        # Create JSON file
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows

        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        # Read with explicit format
        metadata, rows = read_dataset_json(str(json_file), format_name='json')

        assert metadata['name'] == 'TESTDATA'
        assert rows == sample_rows

    def test_read_with_auto_detect_json(self, temp_dir, sample_metadata, sample_rows):
        """Test reading with auto-detected JSON format."""
        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows

        json_file = temp_dir / "test.json"
        with open(json_file, 'w') as f:
            json.dump(dataset, f)

        # Read without specifying format
        metadata, rows = read_dataset_json(str(json_file))

        assert metadata['name'] == 'TESTDATA'
        assert rows == sample_rows

    def test_read_with_auto_detect_ndjson(self, temp_dir, sample_metadata, sample_rows):
        """Test reading with auto-detected NDJSON format."""
        ndjson_file = temp_dir / "test.ndjson"
        with open(ndjson_file, 'w') as f:
            metadata_copy = sample_metadata.copy()
            metadata_copy.pop('rows', None)
            f.write(json.dumps(metadata_copy) + '\n')
            for row in sample_rows:
                f.write(json.dumps(row) + '\n')

        # Read without specifying format
        metadata, rows = read_dataset_json(str(ndjson_file))

        assert metadata['name'] == 'TESTDATA'
        assert rows == sample_rows
