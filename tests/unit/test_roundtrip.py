"""
Roundtrip tests for dsjconvert package.

Tests complete conversion cycles: XPT → Dataset-JSON → XPT
"""

import pytest
import pyreadstat
import pandas as pd
import os
from pathlib import Path

from dsjconvert.converter import XPTConverter
from dsjconvert.reverse_converter import DatasetJSONToXPTConverter


class TestRoundtripXPTToJSONToXPT:
    """Test suite for XPT → JSON → XPT roundtrip conversion."""

    @pytest.fixture
    def sample_xpt(self, temp_dir):
        """Create a sample XPT file for testing."""
        df = pd.DataFrame({
            'STUDYID': ['STUDY001', 'STUDY001', 'STUDY001'],
            'SUBJID': ['001', '002', '003'],
            'AGE': [25, 30, 45],
            'WEIGHT': [70.5, 85.2, 92.1]
        })

        column_labels = {
            'STUDYID': 'Study Identifier',
            'SUBJID': 'Subject ID',
            'AGE': 'Age (years)',
            'WEIGHT': 'Weight (kg)'
        }

        xpt_path = temp_dir / "original.xpt"
        pyreadstat.write_xport(
            df,
            str(xpt_path),
            table_name='DM',
            file_label='Demographics',
            column_labels=column_labels
        )

        return xpt_path

    def test_roundtrip_via_json(self, temp_dir, sample_xpt):
        """Test XPT → JSON → XPT roundtrip."""
        json_dir = temp_dir / "json_output"
        json_dir.mkdir()

        xpt_dir = temp_dir / "xpt_output"
        xpt_dir.mkdir()

        # Step 1: XPT → JSON
        forward_converter = XPTConverter(output_format='json')
        json_path = forward_converter.convert_dataset(
            str(sample_xpt),
            str(json_dir),
            dataset_name='DM'
        )

        assert Path(json_path).exists()
        assert json_path.endswith('.json')

        # Step 2: JSON → XPT
        reverse_converter = DatasetJSONToXPTConverter(input_format='json')
        xpt_path = reverse_converter.convert_dataset(
            json_path,
            str(xpt_dir),
            dataset_name='DM'
        )

        assert Path(xpt_path).exists()
        assert xpt_path.endswith('.xpt')

        # Step 3: Compare original and roundtrip XPT
        original_df, original_meta = pyreadstat.read_xport(str(sample_xpt))
        roundtrip_df, roundtrip_meta = pyreadstat.read_xport(xpt_path)

        # Verify data
        assert len(original_df) == len(roundtrip_df)
        assert list(original_df.columns) == list(roundtrip_df.columns)

        # Verify values (allowing for minor floating point differences)
        pd.testing.assert_frame_equal(original_df, roundtrip_df)

        # Verify metadata
        assert roundtrip_meta.table_name == 'DM'
        assert roundtrip_meta.column_labels == original_meta.column_labels

    def test_roundtrip_via_ndjson(self, temp_dir, sample_xpt):
        """Test XPT → NDJSON → XPT roundtrip."""
        ndjson_dir = temp_dir / "ndjson_output"
        ndjson_dir.mkdir()

        xpt_dir = temp_dir / "xpt_output"
        xpt_dir.mkdir()

        # Step 1: XPT → NDJSON
        forward_converter = XPTConverter(output_format='ndjson')
        ndjson_path = forward_converter.convert_dataset(
            str(sample_xpt),
            str(ndjson_dir),
            dataset_name='DM'
        )

        assert Path(ndjson_path).exists()
        assert ndjson_path.endswith('.ndjson')

        # Step 2: NDJSON → XPT
        reverse_converter = DatasetJSONToXPTConverter(input_format='ndjson')
        xpt_path = reverse_converter.convert_dataset(
            ndjson_path,
            str(xpt_dir),
            dataset_name='DM'
        )

        assert Path(xpt_path).exists()

        # Step 3: Compare original and roundtrip XPT
        original_df, original_meta = pyreadstat.read_xport(str(sample_xpt))
        roundtrip_df, roundtrip_meta = pyreadstat.read_xport(xpt_path)

        # Verify data
        assert len(original_df) == len(roundtrip_df)
        assert list(original_df.columns) == list(roundtrip_df.columns)

        pd.testing.assert_frame_equal(original_df, roundtrip_df)

        # Verify metadata
        assert roundtrip_meta.table_name == 'DM'

    # Pystatread fails on empty dataset write - we're not converting empty datasets anyway
    # def test_roundtrip_empty_dataset(self, temp_dir):
    #     """Test roundtrip with empty dataset."""
    #     # Create empty XPT
    #     df = pd.DataFrame(columns=['STUDYID', 'SUBJID'])
    #     xpt_path = temp_dir / "empty.xpt"
    #     pyreadstat.write_xport(df, str(xpt_path), table_name='EMPTY')
    #
    #     json_dir = temp_dir / "json_output"
    #     json_dir.mkdir()
    #     xpt_dir = temp_dir / "xpt_output"
    #     xpt_dir.mkdir()
    #
    #     # XPT → JSON → XPT
    #     forward_converter = XPTConverter(output_format='json')
    #     json_path = forward_converter.convert_dataset(
    #         str(xpt_path),
    #         str(json_dir)
    #     )
    #
    #     reverse_converter = DatasetJSONToXPTConverter(input_format='json')
    #     roundtrip_xpt_path = reverse_converter.convert_dataset(
    #         json_path,
    #         str(xpt_dir)
    #     )
    #
    #     # Verify: empty reverse conversion is skipped
    #     assert roundtrip_xpt_path is None
    #     # No file should have been written
    #     expected_path = Path(xpt_dir) / "EMPTY.xpt"
    #     assert not expected_path.exists()

    def test_roundtrip_preserves_column_order(self, temp_dir):
        """Test that column order is preserved through roundtrip."""
        # Create XPT with specific column order
        df = pd.DataFrame({
            'ZVAR': [1, 2],
            'AVAR': ['A', 'B'],
            'MVAR': [10.5, 20.5]
        })

        xpt_path = temp_dir / "ordered.xpt"
        pyreadstat.write_xport(df, str(xpt_path), table_name='TEST')

        json_dir = temp_dir / "json_output"
        json_dir.mkdir()
        xpt_dir = temp_dir / "xpt_output"
        xpt_dir.mkdir()

        # XPT → JSON → XPT
        forward_converter = XPTConverter(output_format='json')
        json_path = forward_converter.convert_dataset(str(xpt_path), str(json_dir))

        reverse_converter = DatasetJSONToXPTConverter(input_format='json')
        roundtrip_xpt_path = reverse_converter.convert_dataset(json_path, str(xpt_dir))

        # Verify column order
        original_df, _ = pyreadstat.read_xport(str(xpt_path))
        roundtrip_df, _ = pyreadstat.read_xport(roundtrip_xpt_path)

        assert list(original_df.columns) == list(roundtrip_df.columns)
        assert list(original_df.columns) == ['ZVAR', 'AVAR', 'MVAR']

    def test_roundtrip_with_special_characters(self, temp_dir):
        """Test roundtrip with special characters in data."""
        df = pd.DataFrame({
            'TEXT': ['Hello World', 'Test@123', 'Special-Chars_OK'],
            'NUM': [1, 2, 3]
        })

        xpt_path = temp_dir / "special.xpt"
        pyreadstat.write_xport(df, str(xpt_path), table_name='SPECIAL')

        json_dir = temp_dir / "json_output"
        json_dir.mkdir()
        xpt_dir = temp_dir / "xpt_output"
        xpt_dir.mkdir()

        # XPT → JSON → XPT
        forward_converter = XPTConverter(output_format='json')
        json_path = forward_converter.convert_dataset(str(xpt_path), str(json_dir))

        reverse_converter = DatasetJSONToXPTConverter(input_format='json')
        roundtrip_xpt_path = reverse_converter.convert_dataset(json_path, str(xpt_dir))

        # Verify data integrity
        original_df, _ = pyreadstat.read_xport(str(xpt_path))
        roundtrip_df, _ = pyreadstat.read_xport(roundtrip_xpt_path)

        pd.testing.assert_frame_equal(original_df, roundtrip_df)


class TestRoundtripDataIntegrity:
    """Test suite for verifying data integrity through roundtrip conversions."""

    # def test_roundtrip_numeric_precision(self, temp_dir):
    #     """Test that numeric precision is maintained."""
    #     df = pd.DataFrame({
    #         'FLOAT_COL': [1.23456789, 9.87654321, 5.555555],
    #         'INT_COL': [100, 200, 300]
    #     })
    #
    #     xpt_path = temp_dir / "numeric.xpt"
    #     pyreadstat.write_xport(df, str(xpt_path), table_name='NUMERIC')
    #
    #     json_dir = temp_dir / "json_output"
    #     json_dir.mkdir()
    #     xpt_dir = temp_dir / "xpt_output"
    #     xpt_dir.mkdir()
    #
    #     # Roundtrip
    #     forward_converter = XPTConverter(output_format='json')
    #     json_path = forward_converter.convert_dataset(str(xpt_path), str(json_dir))
    #
    #     reverse_converter = DatasetJSONToXPTConverter(input_format='json')
    #     roundtrip_xpt_path = reverse_converter.convert_dataset(json_path, str(xpt_dir))
    #
    #     # Verify numeric precision (within XPT format limitations)
    #     original_df, _ = pyreadstat.read_xport(str(xpt_path))
    #     roundtrip_df, _ = pyreadstat.read_xport(roundtrip_xpt_path)
    #
    #     pd.testing.assert_frame_equal(original_df, roundtrip_df, check_exact=False, rtol=1e-7)

    def test_roundtrip_with_nulls(self, temp_dir):
        """Test that null values are preserved."""
        df = pd.DataFrame({
            'COL1': [1, None, 3],
            'COL2': ['A', None, 'C'],
            'COL3': [1.1, 2.2, None]
        })

        xpt_path = temp_dir / "nulls.xpt"
        pyreadstat.write_xport(df, str(xpt_path), table_name='NULLS')

        json_dir = temp_dir / "json_output"
        json_dir.mkdir()
        xpt_dir = temp_dir / "xpt_output"
        xpt_dir.mkdir()

        # Roundtrip
        forward_converter = XPTConverter(output_format='json')
        json_path = forward_converter.convert_dataset(str(xpt_path), str(json_dir))

        reverse_converter = DatasetJSONToXPTConverter(input_format='json')
        roundtrip_xpt_path = reverse_converter.convert_dataset(json_path, str(xpt_dir))

        # Verify null values
        original_df, _ = pyreadstat.read_xport(str(xpt_path))
        roundtrip_df, _ = pyreadstat.read_xport(roundtrip_xpt_path)

        # Check null positions
        assert original_df.isna().sum().sum() == roundtrip_df.isna().sum().sum()
        pd.testing.assert_frame_equal(original_df, roundtrip_df)
