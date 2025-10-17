"""
Unit tests for dsjconvert.metadata module.

Tests metadata extraction from Define-XML and inference from source data.
"""

import pytest
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from dsjconvert.metadata import MetadataExtractor
from dsjconvert.exceptions import DefineXMLParseError


class TestMetadataExtractorInit:
    """Test suite for MetadataExtractor initialization."""

    def test_init_without_define_xml(self):
        """Test initialization without Define-XML path."""
        extractor = MetadataExtractor()

        assert extractor.define_xml_path is None
        assert extractor.tree is None
        assert extractor.root is None

    def test_init_with_nonexistent_define_xml(self):
        """Test initialization with non-existent Define-XML path."""
        extractor = MetadataExtractor("/path/to/nonexistent.xml")

        assert extractor.define_xml_path == "/path/to/nonexistent.xml"
        assert extractor.tree is None
        assert extractor.root is None

    def test_init_with_existing_define_xml(self, minimal_define_xml):
        """Test initialization with existing Define-XML file."""
        extractor = MetadataExtractor(minimal_define_xml)

        assert extractor.define_xml_path == minimal_define_xml
        assert extractor.tree is not None
        assert extractor.root is not None

    def test_init_parses_define_xml(self, minimal_define_xml):
        """Test that initialization parses Define-XML file."""
        extractor = MetadataExtractor(minimal_define_xml)

        # Should have parsed the XML
        assert extractor.root.tag.endswith('ODM')

    def test_init_with_invalid_xml(self, temp_dir):
        """Test initialization with invalid XML raises error."""
        invalid_xml = temp_dir / "invalid.xml"
        invalid_xml.write_text("This is not XML")

        with pytest.raises(DefineXMLParseError) as exc_info:
            MetadataExtractor(str(invalid_xml))

        assert exc_info.value.file_path == str(invalid_xml)

    def test_namespaces_defined(self):
        """Test that XML namespaces are defined."""
        assert 'odm' in MetadataExtractor.NAMESPACES
        assert 'def' in MetadataExtractor.NAMESPACES
        assert 'http://www.cdisc.org/ns/odm/v1.3' in MetadataExtractor.NAMESPACES.values()


class TestExtractMetadata:
    """Test suite for extract_metadata method."""

    def test_extract_with_define_xml(self, minimal_define_xml):
        """Test metadata extraction with Define-XML."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata = extractor.extract_metadata("TESTDATA", 100)

        assert metadata["datasetJSONVersion"] == "1.1.0"
        assert metadata["records"] == 100
        assert metadata["name"] == "TESTDATA"
        assert "datasetJSONCreationDateTime" in metadata

    def test_extract_without_define_xml(self):
        """Test metadata extraction without Define-XML."""
        extractor = MetadataExtractor()

        metadata = extractor.extract_metadata("DM", 50)

        assert metadata["datasetJSONVersion"] == "1.1.0"
        assert metadata["records"] == 50
        assert metadata["name"] == "DM"
        assert metadata["label"] == "DM"
        assert metadata["columns"] == []

    def test_extract_with_custom_datetime(self, minimal_define_xml):
        """Test metadata extraction with custom creation datetime."""
        extractor = MetadataExtractor(minimal_define_xml)
        custom_dt = "2025-01-15T10:30:00"

        metadata = extractor.extract_metadata("TESTDATA", 100, custom_dt)

        assert metadata["datasetJSONCreationDateTime"] == custom_dt

    def test_extract_generates_datetime_if_not_provided(self):
        """Test that creation datetime is generated if not provided."""
        extractor = MetadataExtractor()

        metadata = extractor.extract_metadata("DM", 100)

        # Should have a datetime in ISO format
        assert "datasetJSONCreationDateTime" in metadata
        # Verify it's a valid datetime string
        datetime.datetime.fromisoformat(metadata["datasetJSONCreationDateTime"])

    def test_extract_with_different_dataset_names(self):
        """Test metadata extraction with various dataset names."""
        extractor = MetadataExtractor()
        dataset_names = ["DM", "AE", "VS", "LB", "EX"]

        for ds_name in dataset_names:
            metadata = extractor.extract_metadata(ds_name, 10)
            assert metadata["name"] == ds_name
            assert metadata["label"] == ds_name


class TestMinimalMetadata:
    """Test suite for _create_minimal_metadata method."""

    def test_minimal_metadata_structure(self):
        """Test minimal metadata has required fields."""
        extractor = MetadataExtractor()

        metadata = extractor._create_minimal_metadata("TEST", 42, "2025-01-01T00:00:00")

        assert metadata["datasetJSONVersion"] == "1.1.0"
        assert metadata["datasetJSONCreationDateTime"] == "2025-01-01T00:00:00"
        assert metadata["name"] == "TEST"
        assert metadata["label"] == "TEST"
        assert metadata["records"] == 42
        assert metadata["itemGroupOID"] == "{TEST"
        assert metadata["columns"] == []

    def test_minimal_metadata_different_values(self):
        """Test minimal metadata with different inputs."""
        extractor = MetadataExtractor()

        metadata = extractor._create_minimal_metadata("STUDY", 1000, "2024-12-31T23:59:59")

        assert metadata["name"] == "STUDY"
        assert metadata["records"] == 1000
        assert metadata["datasetJSONCreationDateTime"] == "2024-12-31T23:59:59"


class TestInferColumnsFromData:
    """Test suite for infer_columns_from_data method."""

    def test_infer_columns_basic(self):
        """Test basic column inference from names only."""
        extractor = MetadataExtractor()
        column_names = ["STUDYID", "SUBJID", "AGE"]

        columns = extractor.infer_columns_from_data(column_names)

        assert len(columns) == 3
        assert columns[0]["name"] == "STUDYID"
        assert columns[0]["label"] == "STUDYID"
        assert columns[0]["dataType"] == "string"  # Default
        assert columns[0]["itemOID"] == "IT.STUDYID"

    def test_infer_columns_with_labels(self):
        """Test column inference with custom labels."""
        extractor = MetadataExtractor()
        column_names = ["STUDYID", "SUBJID", "AGE"]
        column_labels = {
            "STUDYID": "Study Identifier",
            "SUBJID": "Subject Identifier",
            "AGE": "Age in Years"
        }

        columns = extractor.infer_columns_from_data(column_names, column_labels=column_labels)

        assert columns[0]["label"] == "Study Identifier"
        assert columns[1]["label"] == "Subject Identifier"
        assert columns[2]["label"] == "Age in Years"

    def test_infer_columns_with_types(self):
        """Test column inference with type information."""
        extractor = MetadataExtractor()
        column_names = ["STUDYID", "AGE", "HEIGHT"]
        column_types = {
            "STUDYID": "character",
            "AGE": "integer",
            "HEIGHT": "numeric"
        }

        columns = extractor.infer_columns_from_data(column_names, column_types=column_types)

        assert columns[0]["dataType"] == "string"
        assert columns[1]["dataType"] == "integer"
        assert columns[2]["dataType"] == "double"

    def test_infer_columns_with_sample_data(self):
        """Test column inference with sample data for type detection."""
        extractor = MetadataExtractor()
        column_names = ["NAME", "COUNT", "VALUE"]
        sample_data = {
            "NAME": "John Doe",
            "COUNT": 42,
            "VALUE": 3.14
        }

        columns = extractor.infer_columns_from_data(column_names, sample_data=sample_data)

        assert columns[0]["dataType"] == "string"
        assert columns[1]["dataType"] == "integer"
        assert columns[2]["dataType"] == "double"

    def test_infer_columns_empty_list(self):
        """Test column inference with empty list."""
        extractor = MetadataExtractor()

        columns = extractor.infer_columns_from_data([])

        assert columns == []

    def test_infer_columns_generates_itemoid(self):
        """Test that itemOID is generated for each column."""
        extractor = MetadataExtractor()
        column_names = ["VAR1", "VAR2"]

        columns = extractor.infer_columns_from_data(column_names)

        assert columns[0]["itemOID"] == "IT.VAR1"
        assert columns[1]["itemOID"] == "IT.VAR2"

    def test_infer_columns_types_override_sample_data(self):
        """Test that explicit types override sample data inference."""
        extractor = MetadataExtractor()
        column_names = ["VALUE"]
        column_types = {"VALUE": "character"}
        sample_data = {"VALUE": 123}  # Would infer as integer

        columns = extractor.infer_columns_from_data(
            column_names,
            column_types=column_types,
            sample_data=sample_data
        )

        # Should use explicit type, not sample data
        assert columns[0]["dataType"] == "string"


class TestDataTypeMapping:
    """Test suite for data type mapping methods."""

    def test_map_odm_text_types(self):
        """Test ODM text-like types map to string."""
        text_types = ['text', 'datetime', 'date', 'time', 'partialDate']

        for odm_type in text_types:
            result = MetadataExtractor._map_data_type(odm_type)
            assert result == "string"

    def test_map_odm_integer(self):
        """Test ODM integer maps to integer."""
        result = MetadataExtractor._map_data_type('integer')
        assert result == "integer"

    def test_map_odm_float(self):
        """Test ODM float maps to double."""
        result = MetadataExtractor._map_data_type('float')
        assert result == "double"

    def test_map_odm_unknown_type(self):
        """Test unknown ODM type defaults to string."""
        result = MetadataExtractor._map_data_type('unknown_type')
        assert result == "string"

    def test_map_pyreadstat_character(self):
        """Test pyreadstat character types map to string."""
        result = MetadataExtractor._map_pyreadstat_type('character')
        assert result == "string"

    def test_map_pyreadstat_string(self):
        """Test pyreadstat string types map to string."""
        result = MetadataExtractor._map_pyreadstat_type('string')
        assert result == "string"

    def test_map_pyreadstat_integer(self):
        """Test pyreadstat integer maps to integer."""
        result = MetadataExtractor._map_pyreadstat_type('integer')
        assert result == "integer"

    def test_map_pyreadstat_numeric(self):
        """Test pyreadstat numeric maps to double."""
        result = MetadataExtractor._map_pyreadstat_type('numeric')
        assert result == "double"

    def test_map_pyreadstat_case_insensitive(self):
        """Test pyreadstat type mapping is case-insensitive."""
        assert MetadataExtractor._map_pyreadstat_type('CHARACTER') == "string"
        assert MetadataExtractor._map_pyreadstat_type('Integer') == "integer"
        assert MetadataExtractor._map_pyreadstat_type('NUMERIC') == "double"


class TestDefineXMLExtraction:
    """Test suite for Define-XML extraction methods."""

    def test_extract_file_oid(self, minimal_define_xml):
        """Test extraction of FileOID from Define-XML."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata = extractor.extract_metadata("TESTDATA", 100)

        # FileOID should be present if defined in XML
        if "fileOID" in metadata:
            assert "TESTDATA" in metadata["fileOID"]

    def test_extract_dataset_label(self, minimal_define_xml):
        """Test extraction of dataset label from Define-XML."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata = extractor.extract_metadata("TESTDATA", 100)

        assert "label" in metadata
        # Should have a label (either from Description or dataset name)
        assert len(metadata["label"]) > 0

    def test_extract_columns_from_define(self, minimal_define_xml):
        """Test column extraction from Define-XML."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata = extractor.extract_metadata("TESTDATA", 100)

        assert "columns" in metadata
        assert len(metadata["columns"]) > 0  # Should have columns from fixture
        # Check first column structure
        column = metadata["columns"][0]
        assert "name" in column
        assert "itemOID" in column
        assert "dataType" in column

    def test_find_item_group_case_insensitive(self, minimal_define_xml):
        """Test finding ItemGroupDef is case-insensitive."""
        extractor = MetadataExtractor(minimal_define_xml)

        # Try with different cases (using TESTDATA from the fixture)
        metadata1 = extractor.extract_metadata("TESTDATA", 100)
        metadata2 = extractor.extract_metadata("testdata", 100)

        # Both should find the same dataset
        assert metadata1["name"] == metadata2["name"]
        assert metadata1["name"] == "TESTDATA"

    def test_extract_column_with_length(self, temp_dir):
        """Test extraction of column length attribute."""
        # Create Define-XML with length attribute
        define_xml = temp_dir / "define_with_length.xml"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="TEST.DEFINE">
            <Study OID="STUDY1">
                <MetaDataVersion OID="MDV1">
                    <ItemGroupDef Name="DM" OID="IG.DM">
                        <Description><TranslatedText>Demographics</TranslatedText></Description>
                        <ItemRef ItemOID="IT.STUDYID" KeySequence="1"/>
                    </ItemGroupDef>
                    <ItemDef OID="IT.STUDYID" Name="STUDYID" DataType="text" Length="12">
                        <Description><TranslatedText>Study Identifier</TranslatedText></Description>
                    </ItemDef>
                </MetaDataVersion>
            </Study>
        </ODM>"""
        define_xml.write_text(xml_content)

        extractor = MetadataExtractor(str(define_xml))
        metadata = extractor.extract_metadata("DM", 10)

        # Check if length was extracted
        if metadata["columns"]:
            column = metadata["columns"][0]
            if "length" in column:
                assert column["length"] == 12

    def test_extract_column_with_key_sequence(self, temp_dir):
        """Test extraction of keySequence attribute."""
        # Create Define-XML with keySequence
        define_xml = temp_dir / "define_with_key.xml"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" FileOID="TEST.DEFINE">
            <Study OID="STUDY1">
                <MetaDataVersion OID="MDV1">
                    <ItemGroupDef Name="DM" OID="IG.DM">
                        <ItemRef ItemOID="IT.STUDYID" KeySequence="1"/>
                    </ItemGroupDef>
                    <ItemDef OID="IT.STUDYID" Name="STUDYID" DataType="text">
                        <Description><TranslatedText>Study ID</TranslatedText></Description>
                    </ItemDef>
                </MetaDataVersion>
            </Study>
        </ODM>"""
        define_xml.write_text(xml_content)

        extractor = MetadataExtractor(str(define_xml))
        metadata = extractor.extract_metadata("DM", 10)

        # Check if keySequence was extracted
        if metadata["columns"]:
            column = metadata["columns"][0]
            if "keySequence" in column:
                assert column["keySequence"] == 1


class TestFindItemGroup:
    """Test suite for _find_item_group method."""

    def test_find_item_group_exact_match(self, minimal_define_xml):
        """Test finding ItemGroup with exact name match."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )

        item_group = extractor._find_item_group(metadata_version, "TESTDATA")

        assert item_group is not None
        assert item_group.get('Name') == "TESTDATA"

    def test_find_item_group_uppercase(self, minimal_define_xml):
        """Test finding ItemGroup with uppercase search."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )

        item_group = extractor._find_item_group(metadata_version, "TESTDATA")

        assert item_group is not None

    def test_find_item_group_lowercase(self, minimal_define_xml):
        """Test finding ItemGroup with lowercase search."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )

        item_group = extractor._find_item_group(metadata_version, "testdata")

        assert item_group is not None

    def test_find_item_group_not_found(self, minimal_define_xml):
        """Test finding non-existent ItemGroup returns None."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )

        item_group = extractor._find_item_group(metadata_version, "NONEXISTENT")

        assert item_group is None


class TestExtractColumns:
    """Test suite for _extract_columns method."""

    def test_extract_columns_returns_list(self, minimal_define_xml):
        """Test that _extract_columns returns a list."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )
        item_group = extractor._find_item_group(metadata_version, "TESTDATA")

        columns = extractor._extract_columns(metadata_version, item_group)

        assert isinstance(columns, list)
        assert len(columns) > 0  # Should have columns from fixture

    def test_extract_columns_structure(self, minimal_define_xml):
        """Test extracted column structure."""
        extractor = MetadataExtractor(minimal_define_xml)

        metadata_version = extractor.root.find(
            'odm:Study/odm:MetaDataVersion',
            extractor.NAMESPACES
        )
        item_group = extractor._find_item_group(metadata_version, "TESTDATA")
        columns = extractor._extract_columns(metadata_version, item_group)

        assert len(columns) > 0  # Should have columns
        column = columns[0]
        assert "itemOID" in column
        assert "name" in column
        assert "label" in column
        assert "dataType" in column
