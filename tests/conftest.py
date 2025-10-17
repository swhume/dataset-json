"""
Pytest configuration and shared fixtures for dsjconvert tests.

This module provides fixtures that are available to all test modules.
"""

import pytest
import tempfile
import shutil
import pandas as pd
import datetime
from pathlib import Path
import json


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for test outputs.

    Automatically cleaned up after test completion.

    Returns:
        Path: Path to temporary directory
    """
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_dataframe():
    """
    Create a sample pandas DataFrame with various data types.

    Returns:
        pd.DataFrame: DataFrame with string, integer, float, date columns
    """
    return pd.DataFrame({
        'STUDYID': ['STUDY001', 'STUDY001', 'STUDY001'],
        'SUBJID': ['001', '002', '003'],
        'AGE': [25, 30, 45],
        'WEIGHT': [70.5, 85.2, 92.1],
        'VISITDATE': [
            datetime.date(2024, 1, 15),
            datetime.date(2024, 1, 22),
            datetime.date(2024, 1, 29)
        ]
    })


@pytest.fixture
def sample_dataframe_with_nulls():
    """
    Create a DataFrame with null values for testing null handling.

    Returns:
        pd.DataFrame: DataFrame containing pd.NA values
    """
    return pd.DataFrame({
        'COL1': [1, None, 3],
        'COL2': ['A', 'B', None],
        'COL3': [1.1, None, 3.3]
    })


@pytest.fixture
def sample_metadata():
    """
    Create sample Dataset-JSON metadata structure.

    Returns:
        dict: Valid Dataset-JSON metadata
    """
    return {
        "datasetJSONCreationDateTime": "2025-01-01T12:00:00",
        "datasetJSONVersion": "1.1.0",
        "itemGroupOID": "{TESTDATA",
        "records": 3,
        "name": "TESTDATA",
        "label": "Test Dataset",
        "columns": [
            {
                "itemOID": "IT.TESTDATA.STUDYID",
                "name": "STUDYID",
                "label": "Study Identifier",
                "dataType": "string",
                "length": 8
            },
            {
                "itemOID": "IT.TESTDATA.SUBJID",
                "name": "SUBJID",
                "label": "Subject ID",
                "dataType": "string",
                "length": 10
            },
            {
                "itemOID": "IT.TESTDATA.AGE",
                "name": "AGE",
                "label": "Age",
                "dataType": "integer"
            }
        ]
    }


@pytest.fixture
def sample_rows():
    """
    Create sample row data for Dataset-JSON.

    Returns:
        list: List of rows (each row is a list of values)
    """
    return [
        ["STUDY001", "001", 25],
        ["STUDY001", "002", 30],
        ["STUDY001", "003", 45]
    ]


@pytest.fixture
def minimal_define_xml(temp_dir):
    """
    Create a minimal valid Define-XML file for testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to Define-XML file
    """
    define_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:def="http://www.cdisc.org/ns/def/v2.0"
     FileOID="TEST.DEFINE"
     Originator="Test Organization">
  <Study OID="TEST.STUDY">
    <MetaDataVersion OID="MDV.TEST.1.0">
      <ItemGroupDef OID="IG.TESTDATA" Name="TESTDATA">
        <Description>
          <TranslatedText>Test Dataset</TranslatedText>
        </Description>
        <ItemRef ItemOID="IT.TESTDATA.STUDYID" KeySequence="1"/>
        <ItemRef ItemOID="IT.TESTDATA.SUBJID"/>
        <ItemRef ItemOID="IT.TESTDATA.AGE"/>
      </ItemGroupDef>
      <ItemDef OID="IT.TESTDATA.STUDYID" Name="STUDYID" DataType="text" Length="8">
        <Description>
          <TranslatedText>Study Identifier</TranslatedText>
        </Description>
      </ItemDef>
      <ItemDef OID="IT.TESTDATA.SUBJID" Name="SUBJID" DataType="text" Length="10">
        <Description>
          <TranslatedText>Subject ID</TranslatedText>
        </Description>
      </ItemDef>
      <ItemDef OID="IT.TESTDATA.AGE" Name="AGE" DataType="integer">
        <Description>
          <TranslatedText>Age</TranslatedText>
        </Description>
      </ItemDef>
    </MetaDataVersion>
  </Study>
</ODM>"""

    define_path = temp_dir / "define.xml"
    define_path.write_text(define_xml_content)
    return define_path


@pytest.fixture
def malformed_define_xml(temp_dir):
    """
    Create a malformed Define-XML file for error testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to malformed Define-XML file
    """
    malformed_content = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3">
  <Study OID="TEST">
    <MetaDataVersion>
      <!-- Missing closing tags -->
</ODM>"""

    define_path = temp_dir / "malformed_define.xml"
    define_path.write_text(malformed_content)
    return define_path


@pytest.fixture
def sample_json_output(temp_dir, sample_metadata, sample_rows):
    """
    Create a sample JSON output file for comparison testing.

    Args:
        temp_dir: Temporary directory fixture
        sample_metadata: Sample metadata fixture
        sample_rows: Sample rows fixture

    Returns:
        Path: Path to JSON file
    """
    dataset = sample_metadata.copy()
    dataset["rows"] = sample_rows

    json_path = temp_dir / "test.json"
    with open(json_path, 'w') as f:
        json.dump(dataset, f, indent=2)

    return json_path


@pytest.fixture
def sample_ndjson_output(temp_dir, sample_metadata, sample_rows):
    """
    Create a sample NDJSON output file for comparison testing.

    Args:
        temp_dir: Temporary directory fixture
        sample_metadata: Sample metadata fixture
        sample_rows: Sample rows fixture

    Returns:
        Path: Path to NDJSON file
    """
    ndjson_path = temp_dir / "test.ndjson"

    with open(ndjson_path, 'w') as f:
        # Line 1: Metadata (without rows)
        metadata_copy = sample_metadata.copy()
        metadata_copy.pop('rows', None)
        f.write(json.dumps(metadata_copy) + '\n')

        # Lines 2-n: Rows
        for row in sample_rows:
            f.write(json.dumps(row) + '\n')

    return ndjson_path


@pytest.fixture
def real_test_xpt():
    """
    Provide path to a real test XPT file from the tests directory.

    Returns:
        Path: Path to dm.xpt test file
    """
    return Path("tests/dm.xpt")


@pytest.fixture
def real_define_xml():
    """
    Provide path to the real Define-XML file from the data directory.

    Returns:
        Path: Path to define.xml
    """
    return Path("data/define.xml")


@pytest.fixture
def mock_pyreadstat_metadata():
    """
    Create a mock pyreadstat metadata object for testing.

    Returns:
        object: Mock metadata container with attributes
    """
    class MockMetadata:
        def __init__(self):
            self.number_rows = 3
            self.column_labels = ['Study Identifier', 'Subject ID', 'Age']
            self.variable_to_label = {
                'STUDYID': 'Study Identifier',
                'SUBJID': 'Subject ID',
                'AGE': 'Age'
            }

    return MockMetadata()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
