"""
Unit tests for dsjconvert.validators module.

Tests schema validation for both JSON and NDJSON formats using LinkML.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from dsjconvert.validators import (
    DatasetValidator,
    validate_dataset
)
from dsjconvert.exceptions import SchemaValidationError


class TestDatasetValidator:
    """Test suite for DatasetValidator class."""

    def test_init_default(self):
        """Test validator initialization with default settings."""
        validator = DatasetValidator()
        assert validator.skip_validation is False
        assert validator.schema_paths == {}

    def test_init_skip_validation(self):
        """Test validator initialization with skip_validation=True."""
        validator = DatasetValidator(skip_validation=True)
        assert validator.skip_validation is True

    def test_skip_validation_json(self, sample_metadata, sample_rows):
        """Test that validation is skipped when skip_validation=True."""
        validator = DatasetValidator(skip_validation=True)

        # Even with invalid data, should return True
        invalid_data = {"invalid": "data"}
        result = validator.validate_json(invalid_data, "TEST")

        assert result is True

    def test_skip_validation_ndjson(self, sample_metadata, sample_rows):
        """Test that NDJSON validation is skipped when skip_validation=True."""
        validator = DatasetValidator(skip_validation=True)

        # Even with invalid data, should return True
        result = validator.validate_ndjson({}, [], "TEST")

        assert result is True

    def test_load_schema_caching(self):
        """Test that schema paths are cached after first lookup."""
        validator = DatasetValidator()

        with patch('os.path.exists', return_value=True):
            # First call should find schema path
            path1 = validator._get_schema_path('test.yaml')
            # Second call should use cache
            path2 = validator._get_schema_path('test.yaml')

            assert path1 == path2
            # Should be cached
            assert 'test.yaml' in validator.schema_paths

    def test_load_schema_missing_file(self):
        """Test loading a schema file that doesn't exist."""
        validator = DatasetValidator()

        with patch('os.path.exists', return_value=False):
            path = validator._get_schema_path('nonexistent.yaml')

            assert path is None

    def test_validate_json_with_valid_data(self, sample_metadata, sample_rows):
        """Test JSON validation with valid dataset."""
        validator = DatasetValidator()

        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows

        # Mock schema path and LinkML validation to pass
        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset.yaml'):
            mock_report = MagicMock()
            mock_report.results = []  # Empty results means validation passed
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                result = validator.validate_json(dataset, "TEST")

                assert result is True

    def test_validate_json_with_invalid_data(self):
        """Test JSON validation with invalid dataset."""
        validator = DatasetValidator()

        invalid_dataset = {"missing": "required_fields"}

        # Mock schema path and make LinkML validation fail
        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset.yaml'):
            mock_report = MagicMock()
            mock_result = MagicMock()
            mock_result.message = "Missing required field"
            mock_report.results = [mock_result]  # Non-empty results means validation failed
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                with pytest.raises(SchemaValidationError) as exc_info:
                    validator.validate_json(invalid_dataset, "TEST", raise_on_error=True)

                assert exc_info.value.dataset_name == "TEST"

    def test_validate_json_no_raise(self):
        """Test JSON validation returns False without raising when raise_on_error=False."""
        validator = DatasetValidator()

        invalid_dataset = {"invalid": "data"}

        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset.yaml'):
            mock_report = MagicMock()
            mock_result = MagicMock()
            mock_result.message = "Validation failed"
            mock_report.results = [mock_result]
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                result = validator.validate_json(
                    invalid_dataset,
                    "TEST",
                    raise_on_error=False
                )

                assert result is False

    def test_validate_json_missing_schema(self, sample_metadata, sample_rows):
        """Test JSON validation when schema is missing."""
        validator = DatasetValidator()

        dataset = sample_metadata.copy()
        dataset['rows'] = sample_rows

        # Mock missing schema
        with patch.object(validator, '_get_schema_path', return_value=None):
            result = validator.validate_json(dataset, "TEST")

            # Should return True (validation skipped)
            assert result is True

    def test_validate_ndjson_with_valid_data(self, sample_metadata, sample_rows):
        """Test NDJSON validation with valid data."""
        validator = DatasetValidator()

        # Mock schema path and LinkML validation to pass
        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset-ndjson.yaml'):
            mock_report = MagicMock()
            mock_report.results = []  # Empty results means validation passed
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                result = validator.validate_ndjson(
                    sample_metadata,
                    sample_rows,
                    "TEST"
                )

                assert result is True

    def test_validate_ndjson_with_invalid_data(self, sample_metadata):
        """Test NDJSON validation with invalid metadata."""
        validator = DatasetValidator()

        invalid_metadata = {"invalid": "metadata"}

        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset-ndjson.yaml'):
            mock_report = MagicMock()
            mock_result = MagicMock()
            mock_result.message = "Invalid metadata"
            mock_report.results = [mock_result]
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                with pytest.raises(SchemaValidationError) as exc_info:
                    validator.validate_ndjson(
                        invalid_metadata,
                        [],
                        "TEST",
                        raise_on_error=True
                    )

                assert "TEST" in str(exc_info.value)

    def test_validate_ndjson_fallback_to_json(self, sample_metadata, sample_rows):
        """Test NDJSON validation falls back to JSON schema when NDJSON schema missing."""
        validator = DatasetValidator()

        def mock_get_schema_path(schema_name):
            if schema_name == 'dataset-ndjson.yaml':
                return None  # NDJSON schema missing
            elif schema_name == 'dataset.yaml':
                return '/fake/path/dataset.yaml'  # JSON schema available
            return None

        with patch.object(validator, '_get_schema_path', side_effect=mock_get_schema_path):
            mock_report = MagicMock()
            mock_report.results = []
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                result = validator.validate_ndjson(
                    sample_metadata,
                    sample_rows,
                    "TEST"
                )

                assert result is True

    def test_validate_ndjson_no_raise(self, sample_metadata):
        """Test NDJSON validation returns False without raising when raise_on_error=False."""
        validator = DatasetValidator()

        with patch.object(validator, '_get_schema_path', return_value='/fake/path/dataset-ndjson.yaml'):
            mock_report = MagicMock()
            mock_result = MagicMock()
            mock_result.message = "Validation failed"
            mock_report.results = [mock_result]
            with patch('dsjconvert.validators.validate', return_value=mock_report):
                result = validator.validate_ndjson(
                    sample_metadata,
                    [],
                    "TEST",
                    raise_on_error=False
                )

                assert result is False


class TestValidateDatasetFunction:
    """Test suite for validate_dataset convenience function."""

    def test_validate_json_format(self, sample_metadata, sample_rows):
        """Test convenience function with JSON format."""
        with patch('dsjconvert.validators.DatasetValidator.validate_json', return_value=True) as mock_validate:
            result = validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                format_name='json'
            )

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_ndjson_format(self, sample_metadata, sample_rows):
        """Test convenience function with NDJSON format."""
        with patch('dsjconvert.validators.DatasetValidator.validate_ndjson', return_value=True) as mock_validate:
            result = validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                format_name='ndjson'
            )

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_default_format(self, sample_metadata, sample_rows):
        """Test convenience function uses NDJSON by default."""
        with patch('dsjconvert.validators.DatasetValidator.validate_ndjson', return_value=True) as mock_validate:
            result = validate_dataset(sample_metadata, sample_rows, "TEST")

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_case_insensitive_format(self, sample_metadata, sample_rows):
        """Test format name is case-insensitive."""
        with patch('dsjconvert.validators.DatasetValidator.validate_json', return_value=True) as mock_validate:
            result = validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                format_name='JSON'
            )

            assert result is True
            mock_validate.assert_called_once()

    def test_validate_with_skip_validation(self, sample_metadata, sample_rows):
        """Test convenience function with skip_validation=True."""
        result = validate_dataset(
            sample_metadata,
            sample_rows,
            "TEST",
            skip_validation=True
        )

        # Should skip validation and return True
        assert result is True

    def test_validate_with_raise_on_error_false(self, sample_metadata, sample_rows):
        """Test convenience function with raise_on_error=False."""
        with patch('dsjconvert.validators.DatasetValidator.validate_ndjson', return_value=False):
            result = validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                raise_on_error=False
            )

            assert result is False

    def test_validate_json_creates_complete_dataset(self, sample_metadata, sample_rows):
        """Test JSON format merges metadata and rows into complete dataset."""
        validator_instance = None

        def capture_validator_call(dataset, dataset_name, raise_on_error):
            # Capture the dataset structure
            assert 'rows' in dataset
            assert dataset['rows'] == sample_rows
            assert dataset['name'] == sample_metadata['name']
            return True

        with patch('dsjconvert.validators.DatasetValidator.validate_json', side_effect=capture_validator_call):
            result = validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                format_name='json'
            )

            assert result is True

    def test_validate_multiple_datasets(self, sample_metadata, sample_rows):
        """Test validating multiple datasets in sequence."""
        datasets = ["DM", "AE", "VS", "LB"]

        with patch('dsjconvert.validators.DatasetValidator.validate_ndjson', return_value=True):
            for dataset_name in datasets:
                result = validate_dataset(
                    sample_metadata,
                    sample_rows,
                    dataset_name
                )
                assert result is True

    def test_validate_empty_rows(self, sample_metadata):
        """Test validation with empty rows list."""
        with patch('dsjconvert.validators.DatasetValidator.validate_ndjson', return_value=True) as mock_validate:
            result = validate_dataset(
                sample_metadata,
                [],
                "TEST"
            )

            assert result is True
            # Verify empty rows were passed
            call_args = mock_validate.call_args
            assert call_args[0][1] == []  # rows parameter

    def test_validate_preserves_metadata(self, sample_metadata, sample_rows):
        """Test that validation doesn't modify original metadata."""
        original_metadata = sample_metadata.copy()

        with patch('dsjconvert.validators.DatasetValidator.validate_json', return_value=True):
            validate_dataset(
                sample_metadata,
                sample_rows,
                "TEST",
                format_name='json'
            )

            # Original metadata should be unchanged
            assert sample_metadata == original_metadata
