"""
Schema validation for dsjconvert package.
This module provides functionality to validate Dataset-JSON output
against LinkML YAML schemas for both JSON and NDJSON formats.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from linkml.validator import validate

from .exceptions import SchemaValidationError
from .utils import get_package_resource_path

logger = logging.getLogger(__name__)


class DatasetValidator:
    """
    Validates Dataset-JSON files against their schemas.
    Supports both JSON and NDJSON format validation with graceful
    handling of missing schemas.
    """

    def __init__(self, skip_validation: bool = False):
        """
        Initialize the validator.
        Args:
            skip_validation: If True, validation will be skipped
        """
        self.skip_validation = skip_validation
        self.schema_paths = {}

    def _get_schema_path(self, schema_name: str) -> Optional[str]:
        """
        Get the path to a LinkML YAML schema file.
        Args:
            schema_name: Name of the schema file (e.g., 'dataset.yaml')
        Returns:
            String path to the schema file, or None if not found
        """
        if schema_name in self.schema_paths:
            return self.schema_paths[schema_name]

        # Try package resource path first
        schema_path = get_package_resource_path(os.path.join('schema', schema_name))

        # Try alternative path if package resource path doesn't exist
        if not os.path.exists(schema_path):
            # Try from project root
            project_root = Path(__file__).parent.parent.parent
            schema_path = str(project_root / 'schema' / schema_name)

        if not os.path.exists(schema_path):
            logger.warning(
                f"Schema file not found: {schema_name}. "
                "Validation will be skipped."
            )
            return None

        self.schema_paths[schema_name] = schema_path
        logger.debug(f"Found schema: {schema_path}")
        return schema_path

    def validate_json(
        self,
        dataset: Dict,
        dataset_name: str,
        raise_on_error: bool = True
    ) -> bool:
        """
        Validate a dataset in JSON format against dataset.yaml schema.
        Args:
            dataset: Dataset dictionary with metadata and rows
            dataset_name: Name of the dataset (for error messages)
            raise_on_error: If True, raise exception on validation failure
        Returns:
            bool: True if validation passes or is skipped
        Raises:
            SchemaValidationError: If validation fails and raise_on_error is True
        """
        if self.skip_validation:
            logger.debug(f"Validation skipped for {dataset_name}")
            return True

        schema_path = self._get_schema_path('dataset.yaml')
        if schema_path is None:
            logger.warning(
                f"Schema not available for {dataset_name}, skipping validation"
            )
            return True

        return self._validate_linkml(
            dataset,
            schema_path,
            "Dataset",
            dataset_name,
            raise_on_error
        )

    def validate_ndjson(
        self,
        metadata: Dict,
        rows: List[List],
        dataset_name: str,
        raise_on_error: bool = True,
        batch_size: int = 100
    ) -> bool:
        """
        Validate a dataset in NDJSON format against dataset-ndjson.yaml.
        For NDJSON, we validate the metadata structure separately from row data
        since the format stores them on different lines.
        Args:
            metadata: Dataset metadata dictionary
            rows: List of row data
            dataset_name: Name of the dataset (for error messages)
            raise_on_error: If True, raise exception on validation failure
            batch_size: Number of rows to validate at a time
        Returns:
            bool: True if validation passes or is skipped
        Raises:
            SchemaValidationError: If validation fails and raise_on_error is True
        """
        if self.skip_validation:
            logger.debug(f"Validation skipped for {dataset_name}")
            return True

        schema_path = self._get_schema_path('dataset-ndjson.yaml')
        if schema_path is None:
            logger.warning(
                f"NDJSON schema not available for {dataset_name}, "
                "falling back to JSON schema"
            )
            # Fall back to validating as a complete JSON structure
            dataset = metadata.copy()
            dataset['rows'] = rows
            return self.validate_json(dataset, dataset_name, raise_on_error)

        # Validate metadata (first line of NDJSON)
        metadata_valid = self._validate_linkml(
            metadata,
            schema_path,
            "DatasetMetadata",
            f"{dataset_name} (metadata)",
            raise_on_error
        )

        if not metadata_valid:
            return False

        # Validate rows in batches
        # TODO review just validating the metadata and add a new command for row validation
        # if rows:
        #     return self._validate_ndjson_rows(
        #         rows,
        #         schema_path,
        #         dataset_name,
        #         raise_on_error,
        #         batch_size
        #     )

        return True

    def _validate_linkml(
        self,
        data: Dict,
        schema_path: str,
        target_class: str,
        dataset_name: str,
        raise_on_error: bool
    ) -> bool:
        """
        Perform LinkML validation on data.
        Args:
            data: Data to validate
            schema_path: Path to the LinkML YAML schema file
            target_class: Target class name in the schema
            dataset_name: Name of the dataset (for error messages)
            raise_on_error: If True, raise exception on validation failure
        Returns:
            bool: True if validation passes
        Raises:
            SchemaValidationError: If validation fails and raise_on_error is True
        """
        try:
            report = validate(
                data,
                schema=schema_path,
                target_class=target_class
            )

            if report.results:
                # Validation failed - collect error messages
                error_messages = []
                for result in report.results:
                    error_messages.append(result.message)

                error_msg = "\n".join(f"  - {msg}" for msg in error_messages)
                logger.error(f"Validation failed for {dataset_name}:\n{error_msg}")

                if raise_on_error:
                    raise SchemaValidationError(dataset_name, error_msg)

                return False

            # Validation passed
            logger.info(f"Validation successful for {dataset_name}")
            return True

        except SchemaValidationError:
            raise
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"Validation failed for {dataset_name}: {error_msg}")

            if raise_on_error:
                raise SchemaValidationError(dataset_name, error_msg)

            return False

    def _validate_ndjson_rows(
        self,
        rows: List[List],
        schema_path: str,
        dataset_name: str,
        raise_on_error: bool,
        batch_size: int = 100
    ) -> bool:
        """
        Validate NDJSON row data in batches.
        Args:
            rows: List of row data (each row is a list of values)
            schema_path: Path to the LinkML YAML schema file
            dataset_name: Name of the dataset (for error messages)
            raise_on_error: If True, raise exception on validation failure
            batch_size: Number of rows to validate at a time
        Returns:
            bool: True if validation passes
        Raises:
            SchemaValidationError: If validation fails and raise_on_error is True
        """
        # Process rows in batches
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_start = i + 1  # 1-indexed for user-friendly error messages
            batch_end = min(i + batch_size, len(rows))

            # LinkML expects rows wrapped in a "rows" key for RowData class
            data_row = {"rows": batch}

            try:
                report = validate(
                    data_row,
                    schema=schema_path,
                    target_class="RowData"
                )

                if report.results:
                    # Validation failed for this batch
                    error_messages = []
                    for result in report.results:
                        error_messages.append(result.message)

                    error_msg = (
                        f"Rows {batch_start}-{batch_end}:\n" +
                        "\n".join(f"    - {msg}" for msg in error_messages)
                    )
                    logger.error(
                        f"Validation failed for {dataset_name} {error_msg}"
                    )

                    if raise_on_error:
                        raise SchemaValidationError(dataset_name, error_msg)

                    return False

            except SchemaValidationError:
                raise
            except Exception as e:
                error_msg = (
                    f"Rows {batch_start}-{batch_end}: "
                    f"Validation error: {str(e)}"
                )
                logger.error(f"Validation failed for {dataset_name}: {error_msg}")

                if raise_on_error:
                    raise SchemaValidationError(dataset_name, error_msg)

                return False

        # All batches validated successfully
        logger.debug(f"Validated {len(rows)} rows for {dataset_name}")
        return True


def validate_dataset(
    metadata: Dict,
    rows: List[List],
    dataset_name: str,
    format_name: str = 'ndjson',
    skip_validation: bool = False,
    raise_on_error: bool = True
) -> bool:
    """
    Convenience function to validate a dataset.
    Args:
        metadata: Dataset metadata dictionary
        rows: List of row data
        dataset_name: Name of the dataset
        format_name: Format to validate ('json' or 'ndjson')
        skip_validation: If True, skip validation
        raise_on_error: If True, raise exception on validation failure
    Returns:
        bool: True if validation passes or is skipped
    Raises:
        SchemaValidationError: If validation fails and raise_on_error is True
    """
    validator = DatasetValidator(skip_validation=skip_validation)

    if format_name.lower() == 'json':
        dataset = metadata.copy()
        dataset['rows'] = rows
        return validator.validate_json(dataset, dataset_name, raise_on_error)
    else:
        return validator.validate_ndjson(metadata, rows, dataset_name, raise_on_error)
