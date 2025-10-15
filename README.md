# dsjconvert

**dsjconvert** is a Python package and CLI tool for converting SAS V5 XPORT (XPT) and SAS7BDAT datasets to Dataset-JSON 
v1.1 format. It supports both JSON and NDJSON (newline-delimited JSON) output formats, with NDJSON as the 
default for optimal streaming performance.

## Features

- **Multiple Input Formats**: Convert XPT and SAS7BDAT files
- **Dual Output Formats**: JSON and NDJSON (default)
- **Flexible Metadata**: Use Define-XML metadata or auto-infer from source data
- **Schema Validation**: Built-in validation against Dataset-JSON schemas
- **Comprehensive Logging**: Configurable logging levels for debugging
- **Python Package**: Use as a library in your Python code
- **CLI Tool**: Command-line interface for batch conversions
- **Object-Oriented Design**: Clean, maintainable codebase with single responsibility

## Installation

### From PyPI (when published)

```bash
pip install dsjconvert
```

### From Source

```bash
git clone https://github.com/swhume/dataset-json.git
cd dataset-json
pip install -e .
```

### Dependencies

- Python 3.7+
- pandas
- pyreadstat
- jsonschema

## Quick Start

### As a CLI Tool

Convert XPT files using defaults (NDJSON format):

```bash
dsjconvert -v -x
```

Convert SAS7BDAT files to JSON format:

```bash
dsjconvert -v -b --format json
```

Convert without Define-XML (auto-infer metadata):

```bash
dsjconvert -v -x --no-define
```

### As a Python Library

```python
from dsjconvert import XPTConverter, MetadataExtractor

# With Define-XML metadata
extractor = MetadataExtractor('path/to/define.xml')
converter = XPTConverter(
    metadata_extractor=extractor,
    output_format='ndjson'
)
converter.convert_dataset('input.xpt', 'output_dir')

# Without Define-XML (auto-infer metadata)
converter = XPTConverter(output_format='ndjson')
converter.convert_dataset('input.xpt', 'output_dir')
```

## CLI Usage

### Command-Line Options

| Flag | Name | Description |
| ---- | ---------- | ---------------------------------- |
| -h | --help | Show help message and exit |
| -p | --dsj-path | Directory for Dataset-JSON output (default: ./data) |
| -d | --define | Path to Define-XML file (optional) |
| -s | --sas-path | Directory containing source SAS files (default: ./data) |
| -x | --xpt | Process XPT files (default if neither -x nor -b) |
| -b | --sas | Process SAS7BDAT files |
| --format | | Output format: 'json' or 'ndjson' (default: ndjson) |
| --no-define | | Skip Define-XML and infer metadata from data |
| --validate | | Enable schema validation (default) |
| --no-validate | | Disable schema validation |
| -v | --verbose | Enable verbose output (DEBUG level) |
| --log-level | | Set log level: DEBUG, INFO, WARNING, ERROR |

### Examples

**Basic conversion with verbose output:**

```bash
dsjconvert -v
```

**Convert XPT files with Define-XML:**

```bash
dsjconvert -v -x -d /path/to/define.xml
```

**Convert SAS7BDAT to JSON format:**

```bash
dsjconvert -v -b --format json
```

**Custom paths:**

```bash
dsjconvert -v -x \
  -d /path/to/define.xml \
  -s /path/to/sas/files \
  -p /path/to/output
```

**Convert without Define-XML:**

```bash
dsjconvert -v -x --no-define
```

**Disable validation:**

```bash
dsjconvert -v -x --no-validate
```

## Output Formats

### JSON Format

Traditional JSON format with all data in a single object:

```json
{
  "datasetJSONCreationDateTime": "2025-01-04T16:23:52",
  "datasetJSONVersion": "1.1.0",
  "name": "DM",
  "label": "Demographics",
  "columns": [{"...": "..."}],
  "rows": [
    ["value1", "value2", "..."],
    ["value1", "value2", "..."]
  ]
}
```

### NDJSON Format (Default)

Newline-delimited JSON optimized for streaming:

```
{"datasetJSONCreationDateTime":"2025-01-04T16:23:52","datasetJSONVersion":"1.1.0","name":"DM","columns":[...]}
[value1, value2, ...]
[value1, value2, ...]
```

Line 1 contains metadata, subsequent lines contain one row each as a JSON array. This format allows streaming large datasets without loading everything into memory.

## Working Without Define-XML

If Define-XML is not available, dsjconvert will automatically infer metadata from the source dataset:

- **Column names**: Extracted from the dataset
- **Column labels**: From SAS variable labels (if available)
- **Data types**: Inferred from actual data values
- **Dataset name**: Derived from filename

To explicitly skip Define-XML:

```bash
dsjconvert -v -x --no-define
```

## Library Usage

### Basic Conversion

```python
from dsjconvert import XPTConverter

# Create converter
converter = XPTConverter(output_format='ndjson')

# Convert a single file
output_path = converter.convert_dataset(
    input_path='data/dm.xpt',
    output_dir='output',
    dataset_name='DM'  # Optional, inferred from filename if omitted
)
```

### With Define-XML Metadata

```python
from dsjconvert import XPTConverter, MetadataExtractor

# Initialize metadata extractor
extractor = MetadataExtractor('data/define.xml')

# Create converter with metadata
converter = XPTConverter(
    metadata_extractor=extractor,
    output_format='ndjson',
    skip_validation=False
)

# Convert
output_path = converter.convert_dataset('data/dm.xpt', 'output')
```

### Convert Multiple Files

```python
import os
from dsjconvert import SAS7BDATConverter

converter = SAS7BDATConverter(output_format='json')

# Get all SAS files
sas_dir = 'data'
sas_files = [f for f in os.listdir(sas_dir) if f.endswith('.sas7bdat')]

# Convert each file
for sas_file in sas_files:
    input_path = os.path.join(sas_dir, sas_file)
    output_path = converter.convert_dataset(input_path, 'output')
    print(f"Converted: {output_path}")
```

### Custom Metadata Handling

```python
from dsjconvert import XPTConverter, MetadataExtractor

# Create custom metadata extractor
extractor = MetadataExtractor('define.xml')

# Or extract metadata manually
metadata = extractor.extract_metadata(
    dataset_name='DM',
    num_rows=100
)

# Customize metadata if needed
metadata['originator'] = 'My Organization'

# Use in conversion
converter = XPTConverter(metadata_extractor=extractor)
```

## Architecture

The dsjconvert package follows object-oriented design principles:

### Core Classes

- **DatasetConverter**: Abstract base class for all converters
- **XPTConverter**: Converts SAS V5 XPORT files
- **SAS7BDATConverter**: Converts SAS7BDAT files
- **MetadataExtractor**: Extracts/infers metadata from Define-XML or data
- **WriterFactory**: Creates format-specific writers
- **JSONWriter**: Writes traditional JSON format
- **NDJSONWriter**: Writes NDJSON format
- **DatasetValidator**: Validates output against schemas

### Key Improvements

1. **Replaced XSLT with Python**: Pure Python metadata extraction
2. **Object-Oriented Design**: Clear separation of concerns
3. **Reduced Nesting**: Smaller methods with early returns
4. **Comprehensive Logging**: Debug, info, warning, and error levels
5. **Better Error Handling**: Custom exceptions with context
6. **NDJSON Support**: Streaming-optimized format
7. **Optional Define-XML**: Automatic metadata inference
8. **Package Structure**: Proper Python package with CLI entry point

## Data Type Conversion

SAS dates are converted to Dataset-JSON format:

| SAS Type | Representation | Dataset-JSON Type |
|----------|----------------|-------------------|
| Date | Days since 1960-01-01 | double |
| DateTime | Days + fractional day | double |
| Time | Fractional day | double |
| Integer | Integer value | integer |
| Numeric | Float value | double |
| Character | String value | string |

Example:
- SAS date 0 = 1960-01-01
- SAS datetime 0.5 = 1960-01-01 12:00:00
- SAS time 0.5 = 12:00:00

## Logging

Control logging verbosity:

```bash
# Verbose mode (DEBUG level)
dsjconvert -v -x

# Explicit log level
dsjconvert --log-level INFO -x
```

In Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Error Handling

The package provides detailed error messages:

- **DatasetReadError**: Cannot read source file
- **DefineXMLParseError**: Invalid Define-XML
- **SchemaValidationError**: Output doesn't match schema
- **DatasetConversionError**: General conversion failure

Errors are logged with context for debugging.

## Testing

Run tests with existing test datasets:

```bash
# Test XPT conversion
dsjconvert -v -x -s tests -p output/test

# Test SAS7BDAT conversion
dsjconvert -v -b -s tests -p output/test
```

## Project Structure

```
dataset-json/
├── src/
│   └── dsjconvert/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # Module entry point
│       ├── cli.py               # Command-line interface
│       ├── converter.py         # Dataset converters
│       ├── metadata.py          # Metadata extraction
│       ├── writers.py           # Output writers
│       ├── validators.py        # Schema validation
│       ├── utils.py             # Utility functions
│       ├── exceptions.py        # Custom exceptions
│       └── schemas/             # JSON schemas
│           ├── dataset.schema.json
│           └── dataset-ndjson-schema.json
├── setup.py                     # Package setup
├── requirements.txt             # Dependencies
├── README.md                    # This file
├── data/                        # Default data directory
│   └── define.xml               # Define-XML metadata
├── tests/                       # Test datasets
    └── unit                     # unit tests
└── docs/                        # Documentation

```

## Limitations

- No support for ADaM targetDataType integer dates (planned)
- Uses Define-XML v2.0 (v2.1 support planned)
- Not optimized for very large datasets (>1GB)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE.md for details

## References

- [Dataset-JSON v1.1 Specification](https://github.com/cdisc-org/DataExchange-DatasetJson)
- [NDJSON Specification](http://ndjson.org/)
- [CDISC Standards](https://www.cdisc.org/)

## Changelog

### Version 1.1.0

- Refactored to object-oriented design
- Added NDJSON format support (now default)
- Replaced XSLT with Python code
- Added comprehensive logging
- Made Define-XML optional
- Improved error handling
- Created proper Python package
- Added CLI enhancements
- Reduced method complexity and nesting

### Version 1.0.0

- Initial release
- Basic XPT/SAS7BDAT to JSON conversion
- XSLT-based metadata extraction
- Require Define-XML
