"""
Dataset-JSON readers for dsjconvert package.
This module provides readers for Dataset-JSON v1.1 in both JSON and NDJSON formats.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from .exceptions import DatasetReadError, InvalidFormatError

logger = logging.getLogger(__name__)


class DatasetJSONReader(ABC):
    """
    Abstract base class for Dataset-JSON readers.
    Subclasses must implement the read method for their specific format.
    """

    @abstractmethod
    def read(self, file_path: str) -> Tuple[Dict, List[List]]:
        """
        Read Dataset-JSON file and return metadata and rows.
        Args:
            file_path: Path to the Dataset-JSON file
        Returns:
            Tuple of (metadata dict, list of rows)
        Raises:
            DatasetReadError: If file cannot be read or parsed
        """
        pass


class JSONReader(DatasetJSONReader):
    """
    Reader for traditional JSON format.
    Reads a single JSON object with metadata and rows combined.
    """

    def read(self, file_path: str) -> Tuple[Dict, List[List]]:
        """
        Read Dataset-JSON file in JSON format.
        Args:
            file_path: Path to the JSON file
        Returns:
            Tuple of (metadata dict, list of rows)
        Raises:
            DatasetReadError: If file cannot be read or parsed
        """
        logger.debug(f"Reading JSON format from {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)

            # Extract rows from the dataset
            rows = dataset.pop('rows', [])

            # The remaining data is metadata
            metadata = dataset

            logger.info(
                f"Successfully read JSON dataset from {file_path}: "
                f"{len(rows)} rows, {len(metadata.get('columns', []))} columns"
            )

            return metadata, rows

        except json.JSONDecodeError as e:
            raise DatasetReadError(file_path, f"Invalid JSON format: {e}")
        except IOError as e:
            raise DatasetReadError(file_path, f"Cannot read file: {e}")
        except Exception as e:
            raise DatasetReadError(file_path, f"Unexpected error: {e}")


class NDJSONReader(DatasetJSONReader):
    """
    Reader for NDJSON (Newline-Delimited JSON) format.
    Reads a file where:
    - Line 1: Metadata object
    - Lines 2-n: One JSON array per data row
    """

    def read(self, file_path: str) -> Tuple[Dict, List[List]]:
        """
        Read Dataset-JSON file in NDJSON format.
        Args:
            file_path: Path to the NDJSON file
        Returns:
            Tuple of (metadata dict, list of rows)
        Raises:
            DatasetReadError: If file cannot be read or parsed
        """
        logger.debug(f"Reading NDJSON format from {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                raise DatasetReadError(file_path, "File is empty")

            # Line 1: Metadata
            try:
                metadata = json.loads(lines[0])
            except json.JSONDecodeError as e:
                raise DatasetReadError(
                    file_path,
                    f"Invalid JSON in metadata line (line 1): {e}"
                )

            # Lines 2-n: Rows
            rows = []
            for i, line in enumerate(lines[1:], start=2):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue

                try:
                    row = json.loads(line)
                    if not isinstance(row, list):
                        raise DatasetReadError(
                            file_path,
                            f"Row data must be a JSON array (line {i})"
                        )
                    rows.append(row)
                except json.JSONDecodeError as e:
                    raise DatasetReadError(
                        file_path,
                        f"Invalid JSON in row data (line {i}): {e}"
                    )

            logger.info(
                f"Successfully read NDJSON dataset from {file_path}: "
                f"{len(rows)} rows, {len(metadata.get('columns', []))} columns"
            )

            return metadata, rows

        except DatasetReadError:
            raise
        except IOError as e:
            raise DatasetReadError(file_path, f"Cannot read file: {e}")
        except Exception as e:
            raise DatasetReadError(file_path, f"Unexpected error: {e}")


class ReaderFactory:
    """
    Factory class for creating Dataset-JSON readers.
    This class provides a centralized way to create readers for different
    Dataset-JSON formats.
    """

    # Supported input formats
    FORMATS = {
        'json': JSONReader,
        'ndjson': NDJSONReader
    }

    @classmethod
    def create_reader(cls, format_name: str) -> DatasetJSONReader:
        """
        Create a reader for the specified format.
        Args:
            format_name: Name of the format ('json' or 'ndjson')
        Returns:
            DatasetJSONReader instance for the specified format
        Raises:
            InvalidFormatError: If format_name is not supported
        """
        format_name = format_name.lower()

        if format_name not in cls.FORMATS:
            raise InvalidFormatError(format_name, list(cls.FORMATS.keys()))

        reader_class = cls.FORMATS[format_name]
        logger.debug(f"Created reader for format: {format_name}")
        return reader_class()

    @classmethod
    def create_reader_from_extension(cls, file_path: str) -> DatasetJSONReader:
        """
        Create a reader based on file extension.
        Args:
            file_path: Path to the file
        Returns:
            DatasetJSONReader instance for the detected format
        Raises:
            InvalidFormatError: If file extension is not recognized
        """
        extension = file_path.lower().rsplit('.', 1)[-1]

        if extension == 'json':
            format_name = 'json'
        elif extension == 'ndjson':
            format_name = 'ndjson'
        else:
            raise InvalidFormatError(
                extension,
                ['json', 'ndjson']
            )

        return cls.create_reader(format_name)

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """
        Get a list of supported input formats.
        Returns:
            List of format names
        """
        return list(cls.FORMATS.keys())


def read_dataset_json(file_path: str, format_name: str = None) -> Tuple[Dict, List[List]]:
    """
    Convenience function to read a Dataset-JSON file.
    Args:
        file_path: Path to the Dataset-JSON file
        format_name: Format name ('json' or 'ndjson'). If None, detected from extension.
    Returns:
        Tuple of (metadata dict, list of rows)
    Raises:
        InvalidFormatError: If format is not supported
        DatasetReadError: If file cannot be read
    """
    if format_name:
        reader = ReaderFactory.create_reader(format_name)
    else:
        reader = ReaderFactory.create_reader_from_extension(file_path)

    return reader.read(file_path)
