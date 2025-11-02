# dsjconvert

**dsjconvert** is a Python package and CLI tool for bidirectional conversion between SAS V5 XPORT (XPT) and
Dataset-JSON v1.1 format. It supports both JSON and NDJSON (newline-delimited JSON) formats, with NDJSON as the
default for optimal streaming performance.

## Features

- **Bidirectional Conversion**:
  - Convert XPT and SAS7BDAT files to Dataset-JSON (forward)
  - Convert Dataset-JSON back to XPT format (reverse)
- **Multiple Input Formats**: XPT, SAS7BDAT, JSON, and NDJSON
- **Dual JSON Formats**: JSON and NDJSON (default)
- **Flexible Metadata**: Use Define-XML metadata or auto-infer from source data
- **Schema Validation**: Built-in validation against Dataset-JSON schemas
- **Roundtrip Support**: Full XPT → JSON → XPT conversion cycle
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
- linkml
- jsonschema

## Quick Start

### As a CLI Tool

#### Forward Conversion (SAS to Dataset-JSON)

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

#### Reverse Conversion (Dataset-JSON to XPT)

Convert NDJSON files to XPT:

```bash
dsjconvert -v --to-xpt --input-format ndjson
```

Convert JSON files to XPT:

```bash
dsjconvert -v --to-xpt --input-format json
```

#### Roundtrip Conversion

```bash
# Step 1: XPT to NDJSON
dsjconvert -v -x --format ndjson -s data/xpt -p data/json

# Step 2: NDJSON back to XPT
dsjconvert -v --to-xpt --input-format ndjson -s data/json -p data/xpt_roundtrip
```

### As a Python Library

#### Forward Conversion (SAS to Dataset-JSON)

```python
from dsjconvert import XPTConverter, MetadataExtractor

# With Define-XML metadata
extractor = MetadataExtractor('path/to/define.xml')
converter = XPTConverter(
    metadata_extractor=extractor,
    output_format='ndjson',
    skip_validation=True
)
converter.convert_dataset('input.xpt', 'output_dir')

# Without Define-XML (auto-infer metadata)
converter = XPTConverter(output_format='ndjson')
converter.convert_dataset('input.xpt', 'output_dir')
```

#### Reverse Conversion (Dataset-JSON to XPT)

```python
from dsjconvert import DatasetJSONToXPTConverter

# Convert NDJSON to XPT
converter = DatasetJSONToXPTConverter(input_format='ndjson')
converter.convert_dataset('input.ndjson', 'output_dir')

# Convert JSON to XPT
converter = DatasetJSONToXPTConverter(input_format='json')
converter.convert_dataset('input.json', 'output_dir')

# Using convenience function
from dsjconvert import convert_json_to_xpt

convert_json_to_xpt('input.ndjson', 'output_dir')
```

#### Roundtrip Conversion

```python
from dsjconvert import XPTConverter, DatasetJSONToXPTConverter

# Step 1: XPT → Dataset-JSON
forward = XPTConverter(output_format='ndjson')
json_path = forward.convert_dataset('data/dm.xpt', 'output/json')

# Step 2: Dataset-JSON → XPT
reverse = DatasetJSONToXPTConverter(input_format='ndjson')
xpt_path = reverse.convert_dataset(json_path, 'output/xpt')
```

## CLI Usage

### Command-Line Options

| Flag | Name | Description |
| ---- | ---------- | ---------------------------------- |
| -h | --help | Show help message and exit |
| -p | --dsj-path | Directory for output files (default: ./data) |
| -d | --define | Path to Define-XML file (optional, forward only) |
| -s | --sas-path | Directory containing source files (default: ./data) |
| --to-xpt | | Reverse conversion: Dataset-JSON to XPT |
| -x | --xpt | Process XPT files (forward conversion) |
| -b | --sas | Process SAS7BDAT files (forward conversion) |
| -f, --format | | Output format for forward conversion: 'json' or 'ndjson' (default: ndjson) |
| --input-format | | Input format for reverse conversion: 'json' or 'ndjson' (default: ndjson) |
| --no-define | | Skip Define-XML and infer metadata from data |
| --validate | | Enable schema validation (default) |
| --no-validate | | Disable schema validation |
| -v | --verbose | Enable verbose output (DEBUG level) |
| --log-level | | Set log level: DEBUG, INFO, WARNING, ERROR |

### Examples

#### Forward Conversion (SAS to Dataset-JSON)

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

#### Reverse Conversion (Dataset-JSON to XPT)

**Convert NDJSON files to XPT:**

```bash
dsjconvert -v --to-xpt --input-format ndjson
```

**Convert JSON files to XPT with custom paths:**

```bash
dsjconvert -v --to-xpt \
  --input-format json \
  -s /path/to/json/files \
  -p /path/to/xpt/output
```

**Disable validation during reverse conversion:**

```bash
dsjconvert -v --to-xpt --input-format ndjson --no-validate
```

#### Roundtrip Example

```bash
# Convert XPT to NDJSON
dsjconvert -v -x --format ndjson -s data/xpt -p data/json

# Convert NDJSON back to XPT
dsjconvert -v --to-xpt --input-format ndjson -s data/json -p data/xpt_roundtrip

# Compare original and roundtrip files
# Both should contain identical data
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

## Architecture

The dsjconvert package follows object-oriented design principles:

### Core Classes

#### Forward Conversion (SAS to Dataset-JSON)
- **DatasetConverter**: Abstract base class for all converters
- **XPTConverter**: Converts SAS V5 XPORT files to Dataset-JSON
- **SAS7BDATConverter**: Converts SAS7BDAT files to Dataset-JSON
- **MetadataExtractor**: Extracts/infers metadata from Define-XML or data
- **WriterFactory**: Creates format-specific writers
- **JSONWriter**: Writes traditional JSON format
- **NDJSONWriter**: Writes NDJSON format

#### Reverse Conversion (Dataset-JSON to XPT)
- **DatasetJSONToXPTConverter**: Converts Dataset-JSON files to XPT
- **ReaderFactory**: Creates format-specific readers
- **JSONReader**: Reads traditional JSON format
- **NDJSONReader**: Reads NDJSON format
- **XPTWriter**: Writes SAS V5 XPORT files using pyreadstat

#### Common Components
- **DatasetValidator**: Validates output against schemas

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

## Reverse Conversion Details

### Dataset-JSON to XPT Conversion

The reverse conversion process reads Dataset-JSON files (JSON or NDJSON format) and creates SAS V5 XPORT files:

1. **Read Dataset-JSON**: Parses JSON or NDJSON file to extract metadata and row data
2. **Validate** (optional): Validates against Dataset-JSON v1.1 schema
3. **Convert to DataFrame**: Creates pandas DataFrame from row data with proper column names
4. **Write XPT**: Uses pyreadstat to write XPT file with metadata (table name, labels, etc.)

### Metadata Preservation

The following metadata is preserved during reverse conversion:

- **Dataset name**: Used as XPT table name
- **Dataset label**: Used as XPT file label
- **Column names**: Preserved exactly as in Dataset-JSON
- **Column labels**: Preserved as variable labels in XPT
- **Data values**: All data values are preserved with type integrity

### Data Type Handling

| Dataset-JSON Type | XPT Storage |
|-------------------|-------------|
| string | Character variable |
| integer | Numeric variable |
| double | Numeric variable |
| float | Numeric variable |

Note: SAS date/time conversions (if needed) can be handled by the metadata or post-processing.

## Roundtrip Fidelity

The package supports full roundtrip conversions (XPT → JSON → XPT) with high fidelity:

- ✅ Row data is preserved exactly
- ✅ Column names and order are preserved
- ✅ Column labels are preserved
- ✅ Null values are preserved
- ✅ Numeric precision is preserved (within XPT format limitations)
- ✅ String data is preserved
- ⚠️  Some XPT-specific metadata may not roundtrip (e.g., formats, informats)

See the roundtrip tests in `tests/unit/test_roundtrip.py` for detailed examples.

## Limitations

- No support for ADaM targetDataType integer dates (coming soon)
- Not optimized for very large datasets, >1GB (coming soon)
- XPT format-specific metadata (formats, informats) may not be preserved in roundtrip

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

### Version 0.9.1 (Current)
- Refactored to object-oriented design
- Added NDJSON format support (now default)
- Replaced XSLT with Python code
- Added comprehensive logging
- Made Define-XML optional
- Improved error handling
- Runs as a Python package or CLI tool
- Added CLI enhancements
- Reduced method complexity and nesting
- Bidirectional conversion - Dataset-JSON to XPT reverse conversion
- Roundtrip support (XPT → JSON → XPT)
- Added comprehensive unit tests

### Version 0.8.0

- Initial release
- Basic XPT/SAS7BDAT to JSON conversion
- XSLT-based metadata extraction
- Require Define-XML
