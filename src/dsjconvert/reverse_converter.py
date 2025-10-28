"""
Reverse converter for dsjconvert package.
This module provides conversion from Dataset-JSON v1.1 format back to SAS V5 XPORT (XPT).
"""

import os
import logging
from typing import Dict, List, Optional, Tuple

from .exceptions import DatasetReadError, DatasetConversionError
from .readers import ReaderFactory
from .xpt_writer import XPTWriter, convert_dataset_json_to_dataframe
from .validators import DatasetValidator

logger = logging.getLogger(__name__)


class DatasetJSONToXPTConverter:
    """
    Converter for Dataset-JSON to XPT format.
    This converter reads Dataset-JSON files (JSON or NDJSON) and converts them
    to SAS V5 XPORT (XPT) format using pyreadstat.
    """

    def __init__(
        self,
        input_format: str = 'ndjson',
        skip_validation: bool = False
    ):
        """
        Initialize the reverse converter.
        Args:
            input_format: Input format ('json' or 'ndjson')
            skip_validation: If True, skip schema validation
        """
        self.input_format = input_format
        self.validator = DatasetValidator(skip_validation=skip_validation)
        self.reader = ReaderFactory.create_reader(input_format)
        self.writer = XPTWriter()

    def convert_dataset(
        self,
        input_path: str,
        output_dir: str,
        dataset_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert a Dataset-JSON file to XPT format.
        Args:
            input_path: Path to input Dataset-JSON file
            output_dir: Directory for output XPT file
            dataset_name: Optional dataset name (inferred from filename if not provided)
        Returns:
            str: Path to the output XPT file
        Raises:
            DatasetConversionError: If conversion fails
        """
        if dataset_name is None:
            dataset_name = self._extract_dataset_name(input_path)

        logger.info(f"Converting Dataset-JSON to XPT: {dataset_name}")

        try:
            # Step 1: Read Dataset-JSON file
            metadata, rows = self._read_dataset_json(input_path)
            logger.debug(
                f"Read {len(rows)} rows and {len(metadata.get('columns', []))} columns "
                f"from {input_path}"
            )

            # Step 2: Validate input (optional)
            self._validate_dataset(metadata, rows, dataset_name)

            # Step 2.5: Skip empty datasets
            if not rows:
                logger.warning(
                    f"Dataset '{dataset_name}' has 0 rows; skipping XPT conversion."
                )
                return None

            # Step 3: Convert to DataFrame
            df = convert_dataset_json_to_dataframe(metadata, rows)

            # Step 4: Write to XPT
            output_path = self._write_output(output_dir, dataset_name, df, metadata)

            logger.info(f"Successfully converted {dataset_name} to {output_path}")
            return output_path

        except DatasetReadError:
            raise
        except Exception as e:
            logger.error(f"Failed to convert {dataset_name}: {e}")
            raise DatasetConversionError(dataset_name, str(e))

    def _extract_dataset_name(self, file_path: str) -> str:
        """Extract dataset name from file path."""
        basename = os.path.basename(file_path)
        # Remove both .json and .ndjson extensions
        if basename.lower().endswith('.ndjson'):
            name = basename[:-7]  # Remove .ndjson
        elif basename.lower().endswith('.json'):
            name = basename[:-5]  # Remove .json
        else:
            name = basename.rsplit('.', 1)[0]

        return name.upper()

    def _read_dataset_json(self, file_path: str) -> Tuple[Dict, List[List]]:
        """
        Read Dataset-JSON file.
        Args:
            file_path: Path to Dataset-JSON file
        Returns:
            Tuple of (metadata dict, list of rows)
        Raises:
            DatasetReadError: If file cannot be read
        """
        return self.reader.read(file_path)

    def _validate_dataset(
        self,
        metadata: Dict,
        rows: List[List],
        dataset_name: str
    ) -> bool:
        """
        Validate the dataset against the schema.
        Args:
            metadata: Dataset metadata
            rows: List of rows
            dataset_name: Name of the dataset
        Returns:
            bool: True if validation passes
        """
        if self.input_format.lower() == 'json':
            dataset = metadata.copy()
            dataset['rows'] = rows
            return self.validator.validate_json(
                dataset=dataset,
                dataset_name=dataset_name,
                raise_on_error=False  # Log warnings but don't stop conversion
            )
        else:  # ndjson
            return self.validator.validate_ndjson(
                metadata=metadata,
                rows=rows,
                dataset_name=dataset_name,
                raise_on_error=False  # Log warnings but don't stop conversion
            )

    def _write_output(
        self,
        output_dir: str,
        dataset_name: str,
        df,
        metadata: Dict
    ) -> str:
        """
        Write the converted dataset to XPT file.
        Args:
            output_dir: Output directory
            dataset_name: Name of the dataset
            df: pandas DataFrame
            metadata: Dataset metadata
        Returns:
            str: Path to the output file
        """
        output_path = os.path.join(output_dir, f"{dataset_name}.xpt")
        self.writer.write(output_path, df, metadata)
        return output_path


def convert_json_to_xpt(
    input_path: str,
    output_dir: str,
    input_format: str = None,
    skip_validation: bool = False
) -> Optional[str]:
    """
    Convenience function to convert a Dataset-JSON file to XPT.
    Args:
        input_path: Path to Dataset-JSON file
        output_dir: Directory for output XPT file
        input_format: Input format ('json' or 'ndjson'). If None, detected from extension.
        skip_validation: If True, skip schema validation
    Returns:
        str: Path to the output XPT file
    Raises:
        InvalidFormatError: If format is not supported
        DatasetReadError: If file cannot be read
        DatasetConversionError: If conversion fails
    """
    # Detect format from extension if not provided
    if input_format is None:
        extension = input_path.lower().rsplit('.', 1)[-1]
        if extension == 'json':
            input_format = 'json'
        elif extension == 'ndjson':
            input_format = 'ndjson'
        else:
            # Default to ndjson
            input_format = 'ndjson'

    converter = DatasetJSONToXPTConverter(
        input_format=input_format,
        skip_validation=skip_validation
    )

    return converter.convert_dataset(input_path, output_dir)
