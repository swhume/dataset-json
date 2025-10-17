"""
dsjconvert - SAS to Dataset-JSON Converter

A Python package for converting SAS V5 XPORT (XPT) and SAS7BDAT datasets
to Dataset-JSON v1.1 format, supporting both JSON and NDJSON output formats.

Key Features:
- Convert XPT and SAS7BDAT files to Dataset-JSON
- Support for both JSON and NDJSON (default) formats
- Optional Define-XML metadata extraction
- Automatic metadata inference from source data
- Schema validation
- Comprehensive logging

Usage:
    As a CLI:
        $ dsjconvert -v -x --format ndjson
        $ python -m dsjconvert -v -b

    As a library:
        from dsjconvert import XPTConverter, MetadataExtractor

        extractor = MetadataExtractor('path/to/define.xml')
        converter = XPTConverter(
            metadata_extractor=extractor,
            output_format='ndjson'
        )
        converter.convert_dataset('input.xpt', 'output_dir')
"""

__version__ = "2.0.0"
__author__ = "dsjconvert contributors"
__license__ = "MIT"

# Import main classes for convenient access
from .converter import DatasetConverter, XPTConverter, SAS7BDATConverter
from .metadata import MetadataExtractor
from .writers import WriterFactory, JSONWriter, NDJSONWriter
from .validators import DatasetValidator
from .exceptions import (
    DsjConvertError,
    DefineXMLNotFoundError,
    DefineXMLParseError,
    SchemaValidationError,
    DatasetConversionError,
    DatasetReadError,
    SchemaNotFoundError,
    InvalidFormatError
)

__all__ = [
    # Version
    '__version__',

    # Converters
    'DatasetConverter',
    'XPTConverter',
    'SAS7BDATConverter',

    # Metadata
    'MetadataExtractor',

    # Writers
    'WriterFactory',
    'JSONWriter',
    'NDJSONWriter',

    # Validators
    'DatasetValidator',

    # Exceptions
    'DsjConvertError',
    'DefineXMLNotFoundError',
    'DefineXMLParseError',
    'SchemaValidationError',
    'DatasetConversionError',
    'DatasetReadError',
    'SchemaNotFoundError',
    'InvalidFormatError',
]
