"""
Output writers for dsjconvert package.
This module provides writers for different Dataset-JSON output formats:
- JSON format: Traditional JSON with all data in a single file
- NDJSON format: Newline-delimited JSON for streaming large datasets
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List

from .exceptions import InvalidFormatError

logger = logging.getLogger(__name__)


class DatasetWriter(ABC):
    """
    Abstract base class for dataset writers.
    Subclasses must implement the write method for their specific format.
    """

    @abstractmethod
    def write(self, output_path: str, metadata: Dict, rows: List[List]) -> None:
        """
        Write dataset to file.
        Args:
            output_path: Path where the file should be written
            metadata: Dataset metadata dictionary
            rows: List of row data (each row is a list of values)
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get the file extension for this format.
        Returns:
            File extension including the dot (e.g., '.json', '.ndjson')
        """
        pass


class JSONWriter(DatasetWriter):
    """
    Writer for traditional JSON format.
    Creates a single JSON object with metadata and all rows.
    This is the format used in Dataset-JSON v1.0 and v1.1.
    """

    def write(self, output_path: str, metadata: Dict, rows: List[List]) -> None:
        """
        Write dataset in JSON format.
        Args:
            output_path: Path where the JSON file should be written
            metadata: Dataset metadata dictionary
            rows: List of row data (each row is a list of values)
        """
        logger.debug(f"Writing JSON format to {output_path}")

        # Combine metadata and rows into a single structure
        dataset = metadata.copy()
        dataset["rows"] = rows

        # Write to file with proper formatting
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully wrote JSON dataset to {output_path}")
        except IOError as e:
            logger.error(f"Failed to write JSON file: {e}")
            raise

    def get_file_extension(self) -> str:
        """Get the file extension for JSON format."""
        return '.json'


class NDJSONWriter(DatasetWriter):
    """
    Writer for NDJSON (Newline-Delimited JSON) format.
    Creates a file where:
    - Line 1: Metadata object (dataset attributes + column definitions)
    - Lines 2-n: One JSON array per data row

    This format is optimized for streaming large datasets and is the default
    format for Dataset-JSON v1.1.
    """

    def write(self, output_path: str, metadata: Dict, rows: List[List]) -> None:
        """
        Write dataset in NDJSON format.
        Args:
            output_path: Path where the NDJSON file should be written
            metadata: Dataset metadata dictionary
            rows: List of row data (each row is a list of values)
        """
        logger.debug(f"Writing NDJSON format to {output_path}")

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Line 1: Metadata (without rows field)
                # The metadata contains everything except the actual row data
                metadata_line = metadata.copy()
                # Ensure 'rows' is not in metadata for NDJSON format
                metadata_line.pop('rows', None)

                f.write(json.dumps(metadata_line, ensure_ascii=False))
                f.write('\n')

                # Lines 2-n: One row per line
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False))
                    f.write('\n')

            logger.info(f"Successfully wrote NDJSON dataset to {output_path}")
        except IOError as e:
            logger.error(f"Failed to write NDJSON file: {e}")
            raise

    def get_file_extension(self) -> str:
        """Get the file extension for NDJSON format."""
        return '.ndjson'


class WriterFactory:
    """
    Factory class for creating dataset writers.
    This class provides a centralized way to create writers for different
    output formats.
    """

    # Supported output formats
    FORMATS = {
        'json': JSONWriter,
        'ndjson': NDJSONWriter
    }

    @classmethod
    def create_writer(cls, format_name: str) -> DatasetWriter:
        """
        Create a writer for the specified format.
        Args:
            format_name: Name of the format ('json' or 'ndjson')
        Returns:
            DatasetWriter instance for the specified format
        Raises:
            InvalidFormatError: If format_name is not supported
        """
        format_name = format_name.lower()

        if format_name not in cls.FORMATS:
            raise InvalidFormatError(format_name, list(cls.FORMATS.keys()))

        writer_class = cls.FORMATS[format_name]
        logger.debug(f"Created writer for format: {format_name}")
        return writer_class()

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """
        Get a list of supported output formats.
        Returns:
            List of format names
        """
        return list(cls.FORMATS.keys())

    @classmethod
    def get_default_format(cls) -> str:
        """
        Get the default output format.
        Returns:
            Default format name ('ndjson')
        """
        return 'ndjson'


def write_dataset(
    output_dir: str,
    dataset_name: str,
    metadata: Dict,
    rows: List[List],
    format_name: str = 'ndjson'
) -> str:
    """
    Convenience function to write a dataset in the specified format.
    Args:
        output_dir: Directory where the file should be written
        dataset_name: Name of the dataset (used for filename)
        metadata: Dataset metadata dictionary
        rows: List of row data
        format_name: Output format ('json' or 'ndjson', default: 'ndjson')
    Returns:
        str: Path to the written file
    Raises:
        InvalidFormatError: If format_name is not supported
    """
    writer = WriterFactory.create_writer(format_name)
    extension = writer.get_file_extension()
    output_path = os.path.join(output_dir, f"{dataset_name}{extension}")

    writer.write(output_path, metadata, rows)
    return output_path
