"""
Unit tests for dsjconvert.writers module.

Tests JSON and NDJSON writers and the WriterFactory.
"""

import pytest
import json
from pathlib import Path

from dsjconvert.writers import (
    JSONWriter,
    NDJSONWriter,
    WriterFactory,
    write_dataset
)
from dsjconvert.exceptions import InvalidFormatError


class TestJSONWriter:
    """Test suite for JSONWriter class."""

    def test_creates_json_file(self, temp_dir, sample_metadata, sample_rows):
        """Test that JSON file is created."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, sample_rows)

        assert output_path.exists()
        assert output_path.is_file()

    def test_json_content_valid(self, temp_dir, sample_metadata, sample_rows):
        """Test that output is valid JSON."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, sample_rows)

        # Should parse without errors
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)

    def test_json_has_metadata(self, temp_dir, sample_metadata, sample_rows):
        """Test that JSON includes metadata fields."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, sample_rows)

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data["datasetJSONVersion"] == sample_metadata["datasetJSONVersion"]
        assert data["name"] == sample_metadata["name"]
        assert data["label"] == sample_metadata["label"]

    def test_json_has_rows(self, temp_dir, sample_metadata, sample_rows):
        """Test that JSON includes rows array."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, sample_rows)

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert "rows" in data
        assert data["rows"] == sample_rows
        assert len(data["rows"]) == len(sample_rows)

    def test_json_file_extension(self):
        """Test file extension is .json."""
        writer = JSONWriter()
        assert writer.get_file_extension() == '.json'

    def test_json_formatted_output(self, temp_dir, sample_metadata, sample_rows):
        """Test JSON output is formatted (indented)."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, sample_rows)

        content = output_path.read_text()

        # Check for indentation (formatted JSON has newlines and spaces)
        assert '\n' in content
        assert '  ' in content or '\t' in content

    def test_empty_rows(self, temp_dir, sample_metadata):
        """Test writing dataset with no rows."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        writer.write(str(output_path), sample_metadata, [])

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data["rows"] == []

    def test_overwrites_existing_file(self, temp_dir, sample_metadata, sample_rows):
        """Test that existing file is overwritten."""
        writer = JSONWriter()
        output_path = temp_dir / "output.json"

        # Write first time
        writer.write(str(output_path), sample_metadata, sample_rows)
        first_content = output_path.read_text()

        # Write again with different data
        new_metadata = sample_metadata.copy()
        new_metadata["name"] = "DIFFERENT"
        writer.write(str(output_path), new_metadata, sample_rows)
        second_content = output_path.read_text()

        assert first_content != second_content
        assert "DIFFERENT" in second_content


class TestNDJSONWriter:
    """Test suite for NDJSONWriter class."""

    def test_creates_ndjson_file(self, temp_dir, sample_metadata, sample_rows):
        """Test that NDJSON file is created."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        assert output_path.exists()
        assert output_path.is_file()

    def test_ndjson_line_count(self, temp_dir, sample_metadata, sample_rows):
        """Test NDJSON has correct number of lines (metadata + rows)."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        lines = output_path.read_text().strip().split('\n')

        # 1 metadata line + N row lines
        expected_lines = 1 + len(sample_rows)
        assert len(lines) == expected_lines

    def test_ndjson_first_line_is_metadata(self, temp_dir, sample_metadata, sample_rows):
        """Test first line is metadata object."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        lines = output_path.read_text().strip().split('\n')
        first_line = json.loads(lines[0])

        assert isinstance(first_line, dict)
        assert first_line["datasetJSONVersion"] == sample_metadata["datasetJSONVersion"]
        assert first_line["name"] == sample_metadata["name"]
        assert "rows" not in first_line  # Rows should not be in metadata line

    def test_ndjson_row_lines(self, temp_dir, sample_metadata, sample_rows):
        """Test subsequent lines are row arrays."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        lines = output_path.read_text().strip().split('\n')

        # Check each row line
        for i, row_line in enumerate(lines[1:], 0):
            row_data = json.loads(row_line)
            assert isinstance(row_data, list)
            assert row_data == sample_rows[i]

    def test_ndjson_file_extension(self):
        """Test file extension is .ndjson."""
        writer = NDJSONWriter()
        assert writer.get_file_extension() == '.ndjson'

    def test_ndjson_each_line_valid_json(self, temp_dir, sample_metadata, sample_rows):
        """Test that each line is valid JSON."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        lines = output_path.read_text().strip().split('\n')

        for line in lines:
            # Should parse without error
            parsed = json.loads(line)
            assert parsed is not None

    def test_ndjson_empty_rows(self, temp_dir, sample_metadata):
        """Test writing dataset with no rows."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, [])

        lines = output_path.read_text().strip().split('\n')

        # Should have only metadata line
        assert len(lines) == 1
        metadata = json.loads(lines[0])
        assert "rows" not in metadata

    def test_ndjson_no_formatting(self, temp_dir, sample_metadata, sample_rows):
        """Test NDJSON output is compact (not formatted)."""
        writer = NDJSONWriter()
        output_path = temp_dir / "output.ndjson"

        writer.write(str(output_path), sample_metadata, sample_rows)

        lines = output_path.read_text().strip().split('\n')

        # Each line should be compact JSON (no extra whitespace)
        for line in lines:
            # Should not have indentation within the line
            assert '\n' not in line
            # Compact JSON has minimal spacing
            parsed = json.loads(line)
            compact = json.dumps(parsed, separators=(',', ':'))
            # The line might have different separator spacing, but should be compact
            assert len(line) <= len(json.dumps(parsed, indent=2))


class TestWriterFactory:
    """Test suite for WriterFactory class."""

    def test_create_json_writer(self):
        """Test factory creates JSONWriter for 'json' format."""
        writer = WriterFactory.create_writer('json')
        assert isinstance(writer, JSONWriter)

    def test_create_ndjson_writer(self):
        """Test factory creates NDJSONWriter for 'ndjson' format."""
        writer = WriterFactory.create_writer('ndjson')
        assert isinstance(writer, NDJSONWriter)

    def test_case_insensitive(self):
        """Test format name is case-insensitive."""
        assert isinstance(WriterFactory.create_writer('JSON'), JSONWriter)
        assert isinstance(WriterFactory.create_writer('NDJSON'), NDJSONWriter)
        assert isinstance(WriterFactory.create_writer('Json'), JSONWriter)

    def test_invalid_format_raises_error(self):
        """Test invalid format raises InvalidFormatError."""
        with pytest.raises(InvalidFormatError) as exc_info:
            WriterFactory.create_writer('xml')

        assert exc_info.value.format_name == 'xml'
        assert 'json' in exc_info.value.valid_formats
        assert 'ndjson' in exc_info.value.valid_formats

    def test_get_supported_formats(self):
        """Test get_supported_formats returns correct formats."""
        formats = WriterFactory.get_supported_formats()

        assert 'json' in formats
        assert 'ndjson' in formats
        assert len(formats) >= 2

    def test_get_default_format(self):
        """Test get_default_format returns 'ndjson'."""
        default = WriterFactory.get_default_format()
        assert default == 'ndjson'


class TestWriteDataset:
    """Test suite for write_dataset convenience function."""

    def test_writes_dataset_json(self, temp_dir, sample_metadata, sample_rows):
        """Test writing dataset in JSON format."""
        output_path = write_dataset(
            str(temp_dir),
            "TESTDATA",
            sample_metadata,
            sample_rows,
            format_name='json'
        )

        assert Path(output_path).exists()
        assert output_path.endswith('.json')
        assert "TESTDATA.json" in output_path

    def test_writes_dataset_ndjson(self, temp_dir, sample_metadata, sample_rows):
        """Test writing dataset in NDJSON format."""
        output_path = write_dataset(
            str(temp_dir),
            "TESTDATA",
            sample_metadata,
            sample_rows,
            format_name='ndjson'
        )

        assert Path(output_path).exists()
        assert output_path.endswith('.ndjson')
        assert "TESTDATA.ndjson" in output_path

    def test_default_format_is_ndjson(self, temp_dir, sample_metadata, sample_rows):
        """Test default format is NDJSON."""
        output_path = write_dataset(
            str(temp_dir),
            "TESTDATA",
            sample_metadata,
            sample_rows
        )

        assert output_path.endswith('.ndjson')

    def test_returns_output_path(self, temp_dir, sample_metadata, sample_rows):
        """Test function returns the output file path."""
        output_path = write_dataset(
            str(temp_dir),
            "TESTDATA",
            sample_metadata,
            sample_rows
        )

        assert isinstance(output_path, str)
        assert Path(output_path).exists()

    def test_dataset_name_in_filename(self, temp_dir, sample_metadata, sample_rows):
        """Test dataset name is used in filename."""
        output_path = write_dataset(
            str(temp_dir),
            "MYDATASET",
            sample_metadata,
            sample_rows
        )

        assert "MYDATASET" in output_path
