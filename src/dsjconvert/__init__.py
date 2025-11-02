"""
dsjconvert - Bidirectional SAS and Dataset-JSON Converter

A Python package for converting between SAS V5 XPORT (XPT) and Dataset-JSON v1.1 format,
supporting both JSON and NDJSON formats.

Key Features:
- Convert XPT and SAS7BDAT files to Dataset-JSON
- Convert Dataset-JSON back to XPT format (reverse conversion)
- Support for both JSON and NDJSON (default) formats
- Optional Define-XML metadata extraction
- Automatic metadata inference from source data
- Schema validation
- Comprehensive logging

Usage:
    As a CLI:
        # SAS to Dataset-JSON
        $ dsjconvert -v -x --format ndjson
        $ python -m dsjconvert -v -b

        # Dataset-JSON to XPT (reverse)
        $ dsjconvert -v --to-xpt --input-format ndjson

    As a library:
        # SAS to Dataset-JSON
        from dsjconvert import XPTConverter, MetadataExtractor

        extractor = MetadataExtractor('path/to/define.xml')
        converter = XPTConverter(
            metadata_extractor=extractor,
            output_format='ndjson'
        )
        converter.convert_dataset('input.xpt', 'output_dir')

        # Dataset-JSON to XPT
        from dsjconvert import DatasetJSONToXPTConverter

        converter = DatasetJSONToXPTConverter(input_format='ndjson')
        converter.convert_dataset('input.ndjson', 'output_dir')
"""

__version__ = "1.1.0"
__author__ = "dsjconvert contributors"
__license__ = "MIT"

# Import main classes for convenient access
from .converter import DatasetConverter, XPTConverter, SAS7BDATConverter
from .reverse_converter import DatasetJSONToXPTConverter, convert_json_to_xpt
from .metadata import MetadataExtractor
from .writers import WriterFactory, JSONWriter, NDJSONWriter
from .readers import ReaderFactory, JSONReader, NDJSONReader, read_dataset_json
from .xpt_writer import XPTWriter, write_dataset_json_to_xpt
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

    # Forward Converters (SAS to Dataset-JSON)
    'DatasetConverter',
    'XPTConverter',
    'SAS7BDATConverter',

    # Reverse Converters (Dataset-JSON to XPT)
    'DatasetJSONToXPTConverter',
    'convert_json_to_xpt',

    # Metadata
    'MetadataExtractor',

    # Writers
    'WriterFactory',
    'JSONWriter',
    'NDJSONWriter',
    'XPTWriter',
    'write_dataset_json_to_xpt',

    # Readers
    'ReaderFactory',
    'JSONReader',
    'NDJSONReader',
    'read_dataset_json',

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
