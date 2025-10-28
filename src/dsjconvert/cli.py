"""
Command-line interface for dsjconvert package.
This module provides the CLI functionality with enhanced options for
format selection, validation control, and logging configuration.
"""

import argparse
import os
import sys
import logging
from typing import List

from .converter import XPTConverter, SAS7BDATConverter
from .reverse_converter import DatasetJSONToXPTConverter
from .metadata import MetadataExtractor
# from .writers import WriterFactory
from .exceptions import DsjConvertError

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_level: str = None):
    """
    Configure logging for the application.
    Args:
        verbose: If True, enable verbose (DEBUG) logging
        log_level: Explicit log level (overrides verbose)
    """
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert between SAS datasets and Dataset-JSON format (bidirectional)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SAS to Dataset-JSON conversion
  # Convert XPT files with defaults (output in NDJSON format)
  dsjconvert -v -x

  # Convert SAS7BDAT files to JSON format
  dsjconvert -v -b --format json

  # Convert without Define-XML metadata
  dsjconvert -v -x --no-define

  # Dataset-JSON to XPT conversion (reverse)
  # Convert NDJSON files to XPT
  dsjconvert -v --to-xpt --input-format ndjson

  # Convert JSON files to XPT
  dsjconvert -v --to-xpt --input-format json

  # Custom paths for reverse conversion
  dsjconvert -v --to-xpt --input-format ndjson -s path/to/json -p path/to/output

  # Disable validation
  dsjconvert -v -x --no-validate
        """
    )

    # Input/output paths
    parser.add_argument(
        "-p", "--dsj-path",
        dest="dsj_path",
        help="Directory for Dataset-JSON output files (default: ./data)",
        default=None
    )

    parser.add_argument(
        "-d", "--define",
        dest="define_file",
        help="Path to Define-XML file (optional)",
        default=None
    )

    parser.add_argument(
        "-s", "--sas-path",
        dest="sas_path",
        help="Directory containing source SAS dataset files (default: ./data)",
        default=None
    )

    # Conversion direction
    direction_group = parser.add_mutually_exclusive_group()
    direction_group.add_argument(
        "--to-xpt",
        dest="to_xpt",
        action='store_true',
        help="Reverse conversion: Dataset-JSON to XPT (mutually exclusive with -x/-b)"
    )

    # Input format selection (for SAS to Dataset-JSON)
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "-x", "--xpt",
        dest="is_xpt",
        action='store_true',
        help="Process XPT files (default if neither -x nor -b nor --to-xpt specified)"
    )

    format_group.add_argument(
        "-b", "--sas",
        dest="is_sas",
        action='store_true',
        help="Process SAS7BDAT files"
    )

    # Output format (for SAS to Dataset-JSON conversion)
    parser.add_argument(
        "-f", "--format",
        dest="output_format",
        choices=['json', 'ndjson'],
        default='ndjson',
        help="Output format for SAS to Dataset-JSON conversion (default: ndjson)"
    )

    # Input format (for Dataset-JSON to XPT conversion)
    parser.add_argument(
        "--input-format",
        dest="input_format",
        choices=['json', 'ndjson'],
        default='ndjson',
        help="Input format for Dataset-JSON to XPT conversion (default: ndjson)"
    )

    # Define-XML handling
    parser.add_argument(
        "--no-define",
        dest="no_define",
        action='store_true',
        help="Skip Define-XML and infer metadata from source data"
    )

    # Validation control
    parser.add_argument(
        "--validate",
        dest="validate",
        action='store_true',
        default=True,
        help="Enable schema validation (default)"
    )

    parser.add_argument(
        "--no-validate",
        dest="validate",
        action='store_false',
        help="Disable schema validation"
    )

    # Logging control
    parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action='store_true',
        help="Enable verbose output (DEBUG level)"
    )

    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help="Set explicit log level"
    )

    args = parser.parse_args()

    # Set defaults for paths if not provided
    base_path = os.getcwd()

    if args.dsj_path is None:
        args.dsj_path = os.path.join(base_path, 'data')

    if args.sas_path is None:
        args.sas_path = os.path.join(base_path, 'data')

    if args.define_file is None and not args.no_define:
        args.define_file = os.path.join(base_path, 'data', 'define.xml')

    # If --to-xpt is specified, this is reverse conversion
    if args.to_xpt:
        # For reverse conversion, ensure -x and -b are not used
        if args.is_xpt or args.is_sas:
            parser.error("--to-xpt cannot be used with -x or -b")
    else:
        # If neither format specified for forward conversion, default to XPT
        if not args.is_xpt and not args.is_sas:
            args.is_xpt = True

    return args


def get_dataset_files(directory: str, extension: str) -> List[str]:
    """
    Get list of dataset files in a directory.
    Args:
        directory: Directory to search
        extension: File extension to filter (e.g., '.xpt', '.sas7bdat')
    Returns:
        List of file paths
    Raises:
        ValueError: If no files found
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory not found: {directory}")

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(extension.lower())
    ]

    if not files:
        raise ValueError(
            f"No {extension} files found in {directory}"
        )

    return sorted(files)


def convert_datasets(args):
    """
    Convert all datasets based on CLI arguments.
    Args:
        args: Parsed command-line arguments
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Setup logging
    setup_logging(args.verbose, args.log_level)

    logger.info("=" * 60)
    logger.info("dsjconvert - SAS to Dataset-JSON Converter")
    logger.info("=" * 60)
    logger.info(f"Source directory: {args.sas_path}")
    logger.info(f"Output directory: {args.dsj_path}")
    logger.info(f"Output format: {args.output_format.upper()}")

    # Ensure output directory exists
    os.makedirs(args.dsj_path, exist_ok=True)

    # Initialize metadata extractor
    metadata_extractor = None
    if not args.no_define:
        if args.define_file and os.path.exists(args.define_file):
            logger.info(f"Using Define-XML: {args.define_file}")
            metadata_extractor = MetadataExtractor(args.define_file)
        else:
            logger.warning(
                f"Define-XML not found at {args.define_file}, "
                "will infer metadata from source data"
            )
    else:
        logger.info("Skipping Define-XML as requested")

    # Create converter
    if args.is_xpt:
        logger.info("Processing XPT files...")
        converter = XPTConverter(
            metadata_extractor=metadata_extractor,
            output_format=args.output_format,
            skip_validation=not args.validate
        )
        extension = '.xpt'
    else:
        logger.info("Processing SAS7BDAT files...")
        converter = SAS7BDATConverter(
            metadata_extractor=metadata_extractor,
            output_format=args.output_format,
            skip_validation=not args.validate
        )
        extension = '.sas7bdat'

    # Get list of files to convert
    try:
        files = get_dataset_files(args.sas_path, extension)
        logger.info(f"Found {len(files)} files to convert")
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Convert each file
    successful = []
    failed = []

    for i, file_path in enumerate(files, 1):
        dataset_name = os.path.basename(file_path).rsplit('.', 1)[0].upper()
        logger.info(f"[{i}/{len(files)}] Converting {dataset_name}...")

        try:
            output_path = converter.convert_dataset(
                file_path,
                args.dsj_path,
                dataset_name
            )
            successful.append(dataset_name)
            logger.info(f"  ✓ Success: {output_path}")
        except DsjConvertError as e:
            failed.append(dataset_name)
            logger.error(f"  ✗ Failed: {e}")
        except Exception as e:
            failed.append(dataset_name)
            logger.error(f"  ✗ Unexpected error: {e}", exc_info=args.verbose)

    # Summary
    logger.info("=" * 60)
    logger.info("Conversion Summary")
    logger.info("=" * 60)
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")

    if failed:
        logger.error(f"Failed datasets: {', '.join(failed)}")
        return 1

    logger.info(f"All datasets converted successfully to {args.dsj_path}")
    return 0


def convert_reverse_datasets(args):
    """
    Convert Dataset-JSON files to XPT format based on CLI arguments.
    Args:
        args: Parsed command-line arguments
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Setup logging
    setup_logging(args.verbose, args.log_level)

    logger.info("=" * 60)
    logger.info("dsjconvert - Dataset-JSON to XPT Converter (Reverse)")
    logger.info("=" * 60)
    logger.info(f"Source directory: {args.sas_path}")
    logger.info(f"Output directory: {args.dsj_path}")
    logger.info(f"Input format: {args.input_format.upper()}")

    # Ensure output directory exists
    os.makedirs(args.dsj_path, exist_ok=True)

    # Create reverse converter
    logger.info(f"Processing {args.input_format.upper()} files...")
    converter = DatasetJSONToXPTConverter(
        input_format=args.input_format,
        skip_validation=not args.validate
    )

    # Get list of files to convert
    extension = f'.{args.input_format}'
    try:
        files = get_dataset_files(args.sas_path, extension)
        logger.info(f"Found {len(files)} files to convert")
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Convert each file
    successful = []
    failed = []

    for i, file_path in enumerate(files, 1):
        dataset_name = os.path.basename(file_path).rsplit('.', 1)[0].upper()
        logger.info(f"[{i}/{len(files)}] Converting {dataset_name}...")

        try:
            output_path = converter.convert_dataset(
                file_path,
                args.dsj_path,
                dataset_name
            )
            successful.append(dataset_name)
            logger.info(f"  ✓ Success: {output_path}")
        except DsjConvertError as e:
            failed.append(dataset_name)
            logger.error(f"  ✗ Failed: {e}")
        except Exception as e:
            failed.append(dataset_name)
            logger.error(f"  ✗ Unexpected error: {e}", exc_info=args.verbose)

    # Summary
    logger.info("=" * 60)
    logger.info("Conversion Summary")
    logger.info("=" * 60)
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")

    if failed:
        logger.error(f"Failed datasets: {', '.join(failed)}")
        return 1

    logger.info(f"All datasets converted successfully to {args.dsj_path}")
    return 0


def main():
    """
    Main entry point for the CLI.
    Returns:
        int: Exit code
    """
    try:
        args = parse_arguments()

        # Route to appropriate conversion function
        if args.to_xpt:
            return convert_reverse_datasets(args)
        else:
            return convert_datasets(args)

    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        return 130
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
