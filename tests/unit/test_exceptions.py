"""
Unit tests for dsjconvert.exceptions module.

Tests custom exception classes and their hierarchies.
"""

import pytest
from dsjconvert.exceptions import (
    DsjConvertError,
    DefineXMLNotFoundError,
    DefineXMLParseError,
    SchemaValidationError,
    DatasetConversionError,
    DatasetReadError,
    SchemaNotFoundError,
    InvalidFormatError
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from DsjConvertError."""
        exceptions = [
            DefineXMLNotFoundError("/path/to/define.xml"),
            DefineXMLParseError("/path/to/define.xml", "parse error"),
            SchemaValidationError("DATASET", "validation failed"),
            DatasetConversionError("DATASET", "conversion failed"),
            DatasetReadError("/path/to/file.xpt", "read error"),
            SchemaNotFoundError("/path/to/schema.json"),
            InvalidFormatError("invalid", ["json", "ndjson"])
        ]

        for exc in exceptions:
            assert isinstance(exc, DsjConvertError)
            assert isinstance(exc, Exception)

    def test_base_exception_is_exception(self):
        """Test that DsjConvertError inherits from Exception."""
        exc = DsjConvertError("test error")
        assert isinstance(exc, Exception)


class TestDefineXMLNotFoundError:
    """Test DefineXMLNotFoundError exception."""

    def test_creates_with_file_path(self):
        """Test exception creation with file path."""
        file_path = "/path/to/define.xml"
        exc = DefineXMLNotFoundError(file_path)

        assert exc.file_path == file_path
        assert file_path in str(exc)

    def test_error_message_format(self):
        """Test error message formatting."""
        file_path = "/path/to/define.xml"
        exc = DefineXMLNotFoundError(file_path)
        message = str(exc)

        assert "Define-XML" in message
        assert "not found" in message.lower()
        assert file_path in message

    def test_different_paths(self):
        """Test with different file paths."""
        paths = [
            "define.xml",
            "/abs/path/to/define.xml",
            "C:\\Windows\\Path\\define.xml"
        ]

        for path in paths:
            exc = DefineXMLNotFoundError(path)
            assert exc.file_path == path
            assert path in str(exc)


class TestDefineXMLParseError:
    """Test DefineXMLParseError exception."""

    def test_creates_with_path_and_details(self):
        """Test exception creation with path and error details."""
        file_path = "/path/to/define.xml"
        details = "XML syntax error on line 42"
        exc = DefineXMLParseError(file_path, details)

        assert exc.file_path == file_path
        assert exc.details == details

    def test_error_message_includes_both(self):
        """Test error message includes file path and details."""
        file_path = "define.xml"
        details = "Invalid XML structure"
        exc = DefineXMLParseError(file_path, details)
        message = str(exc)

        assert file_path in message
        assert details in message
        assert "parse" in message.lower() or "failed" in message.lower()


class TestSchemaValidationError:
    """Test SchemaValidationError exception."""

    def test_creates_with_dataset_and_errors(self):
        """Test exception creation with dataset name and validation errors."""
        dataset_name = "DM"
        validation_errors = "Missing required field: datasetJSONVersion"
        exc = SchemaValidationError(dataset_name, validation_errors)

        assert exc.dataset_name == dataset_name
        assert exc.validation_errors == validation_errors

    def test_error_message_format(self):
        """Test error message formatting."""
        dataset_name = "AE"
        validation_errors = "Invalid data type for AGE"
        exc = SchemaValidationError(dataset_name, validation_errors)
        message = str(exc)

        assert dataset_name in message
        assert validation_errors in message
        assert "validation" in message.lower() or "schema" in message.lower()

    def test_multiple_validation_errors(self):
        """Test with multiple validation errors."""
        dataset_name = "VS"
        validation_errors = "Error 1: Missing field\nError 2: Invalid type"
        exc = SchemaValidationError(dataset_name, validation_errors)

        assert validation_errors in str(exc)


class TestDatasetConversionError:
    """Test DatasetConversionError exception."""

    def test_creates_with_dataset_and_details(self):
        """Test exception creation."""
        dataset_name = "LB"
        details = "Column mismatch"
        exc = DatasetConversionError(dataset_name, details)

        assert exc.dataset_name == dataset_name
        assert exc.details == details

    def test_error_message_format(self):
        """Test error message formatting."""
        dataset_name = "EX"
        details = "Failed to convert row 42"
        exc = DatasetConversionError(dataset_name, details)
        message = str(exc)

        assert dataset_name in message
        assert details in message
        assert "convert" in message.lower() or "failed" in message.lower()


class TestDatasetReadError:
    """Test DatasetReadError exception."""

    def test_creates_with_path_and_details(self):
        """Test exception creation."""
        file_path = "/path/to/dataset.xpt"
        details = "File not found"
        exc = DatasetReadError(file_path, details)

        assert exc.file_path == file_path
        assert exc.details == details

    def test_error_message_format(self):
        """Test error message formatting."""
        file_path = "test.xpt"
        details = "Unicode decode error"
        exc = DatasetReadError(file_path, details)
        message = str(exc)

        assert file_path in message
        assert details in message
        assert "read" in message.lower() or "failed" in message.lower()

    def test_with_unicode_errors(self):
        """Test with Unicode decode error details."""
        file_path = "data.xpt"
        details = "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff"
        exc = DatasetReadError(file_path, details)

        assert details in str(exc)


class TestSchemaNotFoundError:
    """Test SchemaNotFoundError exception."""

    def test_creates_with_schema_path(self):
        """Test exception creation."""
        schema_path = "/path/to/schema.json"
        exc = SchemaNotFoundError(schema_path)

        assert exc.schema_path == schema_path

    def test_error_message_format(self):
        """Test error message formatting."""
        schema_path = "dataset.schema.json"
        exc = SchemaNotFoundError(schema_path)
        message = str(exc)

        assert schema_path in message
        assert "schema" in message.lower()
        assert "not found" in message.lower()


class TestInvalidFormatError:
    """Test InvalidFormatError exception."""

    def test_creates_with_format_and_valid_formats(self):
        """Test exception creation."""
        format_name = "xml"
        valid_formats = ["json", "ndjson"]
        exc = InvalidFormatError(format_name, valid_formats)

        assert exc.format_name == format_name
        assert exc.valid_formats == valid_formats

    def test_error_message_includes_all_info(self):
        """Test error message includes invalid format and valid options."""
        format_name = "csv"
        valid_formats = ["json", "ndjson"]
        exc = InvalidFormatError(format_name, valid_formats)
        message = str(exc)

        assert format_name in message
        assert "json" in message
        assert "ndjson" in message
        assert "invalid" in message.lower() or "valid" in message.lower()

    def test_multiple_valid_formats(self):
        """Test with multiple valid formats."""
        format_name = "txt"
        valid_formats = ["json", "ndjson", "xml", "yaml"]
        exc = InvalidFormatError(format_name, valid_formats)
        message = str(exc)

        for fmt in valid_formats:
            assert fmt in message


class TestExceptionCatching:
    """Test exception catching and handling."""

    def test_can_catch_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(DefineXMLNotFoundError):
            raise DefineXMLNotFoundError("/path/to/define.xml")

    def test_can_catch_as_base_exception(self):
        """Test catching any dsjconvert exception as DsjConvertError."""
        with pytest.raises(DsjConvertError):
            raise SchemaValidationError("DATASET", "error")

    def test_can_catch_as_generic_exception(self):
        """Test catching as generic Exception."""
        with pytest.raises(Exception):
            raise DatasetConversionError("DATASET", "error")

    def test_exception_can_be_reraised(self):
        """Test exceptions can be caught and reraised."""
        try:
            raise DatasetReadError("/path/to/file.xpt", "error")
        except DsjConvertError as exc:
            assert isinstance(exc, DatasetReadError)
            # Can access attributes
            assert exc.file_path == "/path/to/file.xpt"


class TestExceptionRepr:
    """Test exception representations."""

    def test_exception_repr(self):
        """Test exception repr is informative."""
        exc = SchemaValidationError("DM", "Invalid schema")
        repr_str = repr(exc)

        # Repr should be evaluable or at least informative
        assert "SchemaValidationError" in repr_str

    def test_exception_str(self):
        """Test exception str is human-readable."""
        exc = DatasetConversionError("AE", "Failed to convert")
        str_msg = str(exc)

        assert len(str_msg) > 0
        assert "AE" in str_msg
        assert "Failed to convert" in str_msg
