"""
Custom exceptions for dsjconvert package.

This module defines custom exception classes for different error scenarios
that can occur during dataset conversion.
"""


class DsjConvertError(Exception):
    """Base exception class for all dsjconvert errors."""
    pass


class DefineXMLNotFoundError(DsjConvertError):
    """Raised when Define-XML file is not found but is required."""
    def __init__(self, file_path):
        self.file_path = file_path
        super().__init__(f"Define-XML file not found: {file_path}")


class DefineXMLParseError(DsjConvertError):
    """Raised when Define-XML file cannot be parsed."""
    def __init__(self, file_path, details):
        self.file_path = file_path
        self.details = details
        super().__init__(f"Failed to parse Define-XML file {file_path}: {details}")


class SchemaValidationError(DsjConvertError):
    """Raised when dataset fails schema validation."""
    def __init__(self, dataset_name, validation_errors):
        self.dataset_name = dataset_name
        self.validation_errors = validation_errors
        super().__init__(
            f"Schema validation failed for dataset {dataset_name}: {validation_errors}"
        )


class DatasetConversionError(DsjConvertError):
    """Raised when dataset conversion fails."""
    def __init__(self, dataset_name, details):
        self.dataset_name = dataset_name
        self.details = details
        super().__init__(f"Failed to convert dataset {dataset_name}: {details}")


class DatasetReadError(DsjConvertError):
    """Raised when source dataset file cannot be read."""
    def __init__(self, file_path, details):
        self.file_path = file_path
        self.details = details
        super().__init__(f"Failed to read dataset file {file_path}: {details}")


class SchemaNotFoundError(DsjConvertError):
    """Raised when schema file is not found."""
    def __init__(self, schema_path):
        self.schema_path = schema_path
        super().__init__(f"Schema file not found: {schema_path}")


class InvalidFormatError(DsjConvertError):
    """Raised when an invalid output format is specified."""
    def __init__(self, format_name, valid_formats):
        self.format_name = format_name
        self.valid_formats = valid_formats
        super().__init__(
            f"Invalid format '{format_name}'. Valid formats: {', '.join(valid_formats)}"
        )
