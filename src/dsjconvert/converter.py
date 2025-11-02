"""
Dataset converter for dsjconvert package.
This module provides the main conversion functionality with an object-oriented
design. It supports converting SAS V5 XPORT (XPT) and SAS7BDAT datasets to
Dataset-JSON format.
"""

import os
import logging
# import json
import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import pyreadstat

from .exceptions import DatasetReadError, DatasetConversionError
from .metadata import MetadataExtractor
from .validators import DatasetValidator
from .writers import WriterFactory
from .utils import datetime_to_integer, match_column_names

logger = logging.getLogger(__name__)


class DatasetConverter(ABC):
    """
    Abstract base class for dataset converters.
    This class provides the common conversion logic for all dataset types.
    Subclasses implement format-specific reading methods.
    """

    def __init__(
        self,
        metadata_extractor: Optional[MetadataExtractor] = None,
        output_format: str = 'ndjson',
        skip_validation: bool = False
    ):
        """
        Initialize the converter.
        Args:
            metadata_extractor: MetadataExtractor instance (optional)
            output_format: Output format ('json' or 'ndjson')
            skip_validation: If True, skip schema validation
        """
        self.metadata_extractor = metadata_extractor
        self.output_format = output_format
        self.validator = DatasetValidator(skip_validation=skip_validation)
        self.writer = WriterFactory.create_writer(output_format)

    @abstractmethod
    def read_dataset(self, file_path: str) -> Tuple[pd.DataFrame, pyreadstat._readstat_parser.metadata_container]:
        """
        Read a dataset file and return dataframe and metadata.
        Args:
            file_path: Path to the dataset file
        Returns:
            Tuple of (DataFrame, metadata)
        Raises:
            DatasetReadError: If file cannot be read
        """
        pass

    def convert_dataset(
        self,
        input_path: str,
        output_dir: str,
        dataset_name: Optional[str] = None
    ) -> str:
        """
        Convert a single dataset file to Dataset-JSON format.
        Args:
            input_path: Path to input dataset file
            output_dir: Directory for output files
            dataset_name: Optional dataset name (inferred from filename if not provided)
        Returns:
            str: Path to the output file
        Raises:
            DatasetConversionError: If conversion fails
        """
        if dataset_name is None:
            dataset_name = self._extract_dataset_name(input_path)

        logger.info(f"Converting dataset: {dataset_name}")

        try:
            # Step 1: Read source dataset
            df, meta = self.read_dataset(input_path)
            logger.debug(
                f"Read {len(df)} rows and {len(df.columns)} columns from {input_path}"
            )

            # Step 2: Extract or infer metadata
            metadata = self._extract_metadata(dataset_name, meta, df)

            # Step 3: Convert data rows
            rows = self._convert_rows(df, metadata)

            # Step 4: Validate
            self._validate_dataset(metadata, rows, dataset_name)

            # Step 5: Write output
            output_path = self._write_output(output_dir, dataset_name, metadata, rows)

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
        name = basename.rsplit('.', 1)[0]
        return name.upper()

    def _extract_metadata(
        self,
        dataset_name: str,
        meta: pyreadstat._readstat_parser.metadata_container,
        df: pd.DataFrame
    ) -> Dict:
        """
        Extract or infer metadata for the dataset.
        Args:
            dataset_name: Name of the dataset
            meta: Metadata from pyreadstat
            df: DataFrame containing the data
        Returns:
            Dict containing Dataset-JSON metadata
        """
        num_rows = meta.number_rows if meta else len(df)

        # Try to extract from Define-XML if available
        if self.metadata_extractor:
            metadata = self.metadata_extractor.extract_metadata(
                dataset_name, num_rows
            )
        else:
            # Create minimal metadata
            metadata = {
                "datasetJSONCreationDateTime": datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "datasetJSONVersion": "1.1.0",
                "itemGroupOID": f"IG.{dataset_name}",
                "records": num_rows,
                "name": dataset_name,
                "label": dataset_name,
                "columns": []
            }

        # If columns are empty, infer from data
        if not metadata.get('columns'):
            metadata['columns'] = self._infer_columns(df, meta, dataset_name)

        return metadata

    def _infer_columns(
        self,
        df: pd.DataFrame,
        meta: pyreadstat._readstat_parser.metadata_container,
        dataset_name: str
    ) -> List[Dict]:
        """
        Infer column definitions from DataFrame and metadata.
        Args:
            df: DataFrame containing the data
            meta: Metadata from pyreadstat
        Returns:
            List of column definition dictionaries
        """
        column_names = df.columns.tolist()

        # Get labels from pyreadstat metadata if available
        # pyreadstat returns column_labels as a list parallel to column_names
        column_labels_dict = None
        if meta and hasattr(meta, 'column_labels') and meta.column_labels:
            column_labels_dict = dict(zip(column_names, meta.column_labels))

        # Get sample data for type inference
        sample_data = {}
        if len(df) > 0:
            first_row = df.iloc[0]
            sample_data = {col: first_row[col] for col in df.columns}

        # Use metadata extractor if available
        if self.metadata_extractor:
            return self.metadata_extractor.infer_columns_from_data(
                column_names,
                dataset_name=dataset_name,
                column_labels=column_labels_dict,
                sample_data=sample_data
            )
        else:
            # Simple inference without metadata extractor
            from .utils import infer_data_type
            columns = []
            for col in column_names:
                label = column_labels_dict.get(col, col) if column_labels_dict else col
                data_type = infer_data_type(sample_data.get(col)) or "string"

                columns.append({
                    "itemOID": f"IT.{dataset_name}.{col}",
                    "name": col,
                    "label": label,
                    "dataType": data_type
                })
            return columns

    def _convert_rows(self, df: pd.DataFrame, metadata: Dict) -> List[List]:
        """
        Convert DataFrame rows to Dataset-JSON format.
        Args:
            df: DataFrame containing the data
            metadata: Dataset metadata
        Returns:
            List of rows (each row is a list of values)
        """
        if len(df) == 0:
            logger.debug("Dataset has no rows")
            return []

        # Build a mapping of column names to data types
        column_types = {
            col['name']: col['dataType']
            for col in metadata['columns']
        }

        # Match source columns with metadata columns
        try:
            column_mapping = match_column_names(
                df.columns.tolist(),
                list(column_types.keys())
            )
        except ValueError as e:
            logger.error(f"Column matching failed: {e}")
            raise

        rows = []
        for index, row in df.iterrows():
            converted_row = self._convert_row(row, column_mapping, column_types)
            rows.append(converted_row)

        logger.debug(f"Converted {len(rows)} rows")
        return rows

    def _convert_row(
        self,
        row: pd.Series,
        column_mapping: Dict[str, str],
        column_types: Dict[str, str]
    ) -> List:
        """
        Convert a single row to Dataset-JSON format.
        Args:
            row: Pandas Series representing a row
            column_mapping: Mapping of source column names to metadata column names
            column_types: Mapping of column names to data types
        Returns:
            List of converted values
        """
        converted = []

        for source_col in row.index:
            metadata_col = column_mapping[source_col]
            data_type = column_types[metadata_col]
            value = row[source_col]

            converted_value = self._convert_value(value, data_type)
            converted.append(converted_value)

        return converted

    def _convert_value(self, value, data_type: str):
        """
        Convert a single value to Dataset-JSON format.
        Args:
            value: The value to convert
            data_type: Target data type
        Returns:
            Converted value (or None for null values)
        """
        # Handle datetime types first (before null check)
        if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
            return datetime_to_integer(value)

        # Handle null/NA values
        if pd.isna(value):
            return None

        # Handle by data type
        if data_type == "integer":
            if value == "":
                return None
            return int(value)

        elif data_type == "string":
            return str(value) if value is not None else None

        else:  # double, float, etc.
            return float(value) if value != "" else None

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
        if self.output_format.lower() == 'json':
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
        metadata: Dict,
        rows: List[List]
    ) -> str:
        """
        Write the converted dataset to a file.
        Args:
            output_dir: Output directory
            dataset_name: Name of the dataset
            metadata: Dataset metadata
            rows: List of rows
        Returns:
            str: Path to the output file
        """
        extension = self.writer.get_file_extension()
        output_path = os.path.join(output_dir, f"{dataset_name}{extension}")

        self.writer.write(output_path, metadata, rows)
        return output_path


class XPTConverter(DatasetConverter):
    """Converter for SAS V5 XPORT (XPT) files."""

    def read_dataset(self, file_path: str) -> Tuple[pd.DataFrame, pyreadstat._readstat_parser.metadata_container]:
        """
        Read an XPT file.
        Args:
            file_path: Path to the XPT file
        Returns:
            Tuple of (DataFrame, metadata)
        Raises:
            DatasetReadError: If file cannot be read
        """
        try:
            logger.debug(f"Reading XPT file: {file_path}")
            df, meta = pyreadstat.read_xport(file_path, encoding="WINDOWS-1252")
            return df, meta
        except UnicodeDecodeError as e:
            raise DatasetReadError(file_path, f"Unicode decode error: {e}")
        except Exception as e:
            raise DatasetReadError(file_path, str(e))


class SAS7BDATConverter(DatasetConverter):
    """Converter for SAS7BDAT files."""

    def read_dataset(self, file_path: str) -> Tuple[pd.DataFrame, pyreadstat._readstat_parser.metadata_container]:
        """
        Read a SAS7BDAT file.
        Args:
            file_path: Path to the SAS7BDAT file
        Returns:
            Tuple of (DataFrame, metadata)
        Raises:
            DatasetReadError: If file cannot be read
        """
        try:
            logger.debug(f"Reading SAS7BDAT file: {file_path}")
            df, meta = pyreadstat.read_sas7bdat(file_path)
            return df, meta
        except Exception as e:
            raise DatasetReadError(file_path, str(e))
