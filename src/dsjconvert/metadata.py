"""
Metadata extraction for dsjconvert package.
This module provides functionality to extract Dataset-JSON metadata from
Define-XML files or infer it from source datasets when Define-XML is not available.
This replaces the XSLT transformation in the original implementation.
"""

import os
import logging
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re

# from .exceptions import DefineXMLNotFoundError, DefineXMLParseError
from .exceptions import DefineXMLParseError
from .utils import infer_data_type

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extracts metadata from Define-XML or infers it from source datasets.
    This class replaces the XSLT transformation with pure Python code,
    providing better error handling and flexibility.
    Supports both Define-XML v2.0 and v2.1 specifications.
    """

    # Base XML namespaces - will be updated dynamically during parsing
    NAMESPACES = {
        'odm': 'http://www.cdisc.org/ns/odm/v1.3',
        'def': None,  # Will be detected from document
        'xlink': 'http://www.w3.org/1999/xlink'
    }

    def __init__(self, define_xml_path: Optional[str] = None):
        """
        Initialize the MetadataExtractor.
        Args:
            define_xml_path: Path to Define-XML file (optional)
        """
        self.define_xml_path = define_xml_path
        self.tree = None
        self.root = None
        self.define_version = None  # Will store detected version (2.0 or 2.1)
        self.namespaces = self.NAMESPACES.copy()  # Instance copy

        if define_xml_path and os.path.exists(define_xml_path):
            self._parse_define_xml()

    def _parse_define_xml(self):
        """Parse the Define-XML file, detect version, and store the tree."""
        try:
            logger.info(f"Parsing Define-XML file: {self.define_xml_path}")
            self.tree = ET.parse(self.define_xml_path)
            self.root = self.tree.getroot()

            # Detect namespaces from the root element
            self._detect_namespaces()

            # Detect Define-XML version
            self._detect_define_version()

            logger.info(f"Successfully parsed Define-XML v{self.define_version}")
        except ET.ParseError as e:
            raise DefineXMLParseError(self.define_xml_path, str(e))
        except Exception as e:
            raise DefineXMLParseError(self.define_xml_path, str(e))

    def _detect_namespaces(self):
        """
        Detect and extract namespaces from the XML document.
        Updates the instance namespaces dictionary with actual URIs from the document.
        """
        # ElementTree doesn't expose xmlns attributes easily, so we parse the raw file
        # to extract namespace declarations
        try:
            with open(self.define_xml_path, 'r', encoding='utf-8') as f:
                # Read first few lines to find namespace declarations
                content = f.read(4096)  # Read first 4KB which should contain ODM element

                # Extract xmlns declarations using regex
                # Match xmlns:prefix="uri" or xmlns="uri"
                xmlns_pattern = r'xmlns:?(\w+)?="([^"]+)"'
                matches = re.findall(xmlns_pattern, content)

                for prefix, uri in matches:
                    if not prefix:  # Default namespace
                        self.namespaces['odm'] = uri
                    else:
                        self.namespaces[prefix] = uri

        except Exception as e:
            logger.warning(f"Could not extract namespaces from file: {e}")

        # Also extract namespace from the root tag (default namespace)
        root_tag = self.root.tag
        if root_tag.startswith('{'):
            ns_uri = root_tag.split('}')[0][1:]
            self.namespaces['odm'] = ns_uri

        logger.debug(f"Detected namespaces: {self.namespaces}")

    def _detect_define_version(self):
        """
        Detect Define-XML version from namespace URI.
        Sets self.define_version to "2.0", "2.1", or None.
        """
        def_ns = self.namespaces.get('def', '') or ''

        if 'v2.0' in def_ns:
            self.define_version = "2.0"
        elif 'v2.1' in def_ns:
            self.define_version = "2.1"
        elif 'v2.x' in def_ns or ('/def/v2' in def_ns and def_ns):
            # Generic v2.x namespace - try to determine from MetaDataVersion
            self.define_version = self._detect_version_from_metadata()
        elif not def_ns:
            # No def namespace found - try to detect from metadata structure
            logger.debug("No def namespace found, detecting from metadata structure")
            self.define_version = self._detect_version_from_metadata()
        else:
            logger.warning(f"Unable to determine Define-XML version from namespace: {def_ns}")
            self.define_version = None

        logger.debug(f"Detected Define-XML version: {self.define_version}")

    def _detect_version_from_metadata(self):
        """
        Fallback method to detect version from MetaDataVersion structure.
        v2.1 uses def:Standards element, v2.0 uses def:StandardName attribute.
        """
        # Try to find MetaDataVersion
        study = self.root.find(f'odm:Study', self.namespaces)
        if study is not None:
            mdv = study.find(f'odm:MetaDataVersion', self.namespaces)
            if mdv is not None:
                # Check for v2.1 Standards element
                def_ns = self.namespaces.get('def', '')
                if def_ns:
                    standards = mdv.find(f'def:Standards')
                    if standards is not None:
                        return "2.1"

                # Check for v2.0 StandardName attribute
                for attr in mdv.attrib:
                    if 'StandardName' in attr:
                        return "2.0"

        # Default to 2.0 if unable to determine
        return "2.0"

    def extract_metadata(
        self,
        dataset_name: str,
        num_rows: int,
        creation_datetime: Optional[str] = None
    ) -> Dict:
        """
        Extract or infer metadata for a dataset.
        Args:
            dataset_name: Name of the dataset
            num_rows: Number of rows in the dataset
            creation_datetime: ISO format creation datetime (defaults to now)
        Returns:
            Dict containing Dataset-JSON metadata structure
        """
        if creation_datetime is None:
            creation_datetime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if self.root is not None:
            return self._extract_from_define_xml(
                dataset_name, num_rows, creation_datetime
            )
        else:
            logger.warning(
                f"No Define-XML available for {dataset_name}, "
                "metadata will be inferred from source data"
            )
            return self._create_minimal_metadata(
                dataset_name, num_rows, creation_datetime
            )

    def _extract_from_define_xml(
        self,
        dataset_name: str,
        num_rows: int,
        creation_datetime: str
    ) -> Dict:
        """
        Extract metadata from Define-XML file.
        This method replicates the XSLT transformation logic in pure Python.
        Args:
            dataset_name: Name of the dataset
            num_rows: Number of rows in the dataset
            creation_datetime: ISO format creation datetime
        Returns:
            Dict containing Dataset-JSON metadata
        """
        metadata = {
            "datasetJSONCreationDateTime": creation_datetime,
            "datasetJSONVersion": "1.1.0"
        }

        # Extract file-level attributes
        file_oid = self.root.get('FileOID')
        originator = self.root.get('Originator')

        if file_oid:
            metadata["fileOID"] = f"{file_oid}.{dataset_name}"

        if originator:
            metadata["originator"] = originator

        # Find the Study element
        study = self.root.find('odm:Study', self.namespaces)
        if study is None:
            logger.warning("No Study element found in Define-XML")
            return self._create_minimal_metadata(
                dataset_name, num_rows, creation_datetime
            )

        study_oid = study.get('OID')
        if study_oid:
            metadata["studyOID"] = study_oid

        # Find MetaDataVersion
        metadata_version = study.find('odm:MetaDataVersion', self.namespaces)
        if metadata_version is None:
            logger.warning("No MetaDataVersion element found in Define-XML")
            return self._create_minimal_metadata(
                dataset_name, num_rows, creation_datetime
            )

        metadata_version_oid = metadata_version.get('OID')
        if metadata_version_oid:
            metadata["metaDataVersionOID"] = metadata_version_oid

        # Find the ItemGroupDef for this dataset
        item_group = self._find_item_group(metadata_version, dataset_name)
        if item_group is None:
            logger.warning(
                f"No ItemGroupDef found for dataset {dataset_name} in Define-XML"
            )
            return self._create_minimal_metadata(
                dataset_name, num_rows, creation_datetime
            )

        # Extract dataset-level metadata
        metadata["itemGroupOID"] = f"IG.{item_group.get('Name', dataset_name)}"
        metadata["records"] = num_rows
        metadata["name"] = item_group.get('Name', dataset_name)

        # Extract label
        desc = item_group.find('odm:Description/odm:TranslatedText', self.namespaces)
        metadata["label"] = desc.text if desc is not None else dataset_name
        metadata["columns"] = self._extract_columns(metadata_version, item_group)

        return metadata

    def _find_item_group(self, metadata_version, dataset_name: str):
        """
        Find the ItemGroupDef element for a dataset.
        Uses case-insensitive matching.
        Args:
            metadata_version: MetaDataVersion XML element
            dataset_name: Name of the dataset
        Returns:
            ItemGroupDef XML element or None
        """
        dataset_name_upper = dataset_name.upper()

        for item_group in metadata_version.findall('odm:ItemGroupDef', self.namespaces):
            name = item_group.get('Name', '')
            if name.upper() == dataset_name_upper:
                return item_group

        return None

    def _extract_columns(self, metadata_version, item_group) -> List[Dict]:
        """
        Extract column definitions from ItemGroupDef.
        Args:
            metadata_version: MetaDataVersion XML element
            item_group: ItemGroupDef XML element
        Returns:
            List of column definition dictionaries
        """
        columns = []

        for item_ref in item_group.findall('odm:ItemRef', self.namespaces):
            item_oid = item_ref.get('ItemOID')

            # Find the corresponding ItemDef
            item_def = metadata_version.find(
                f"odm:ItemDef[@OID='{item_oid}']",
                self.namespaces
            )

            if item_def is None:
                logger.warning(f"ItemDef not found for ItemOID: {item_oid}")
                continue

            column = self._extract_column_definition(item_def, item_ref)
            columns.append(column)

        return columns

    def _extract_column_definition(self, item_def, item_ref) -> Dict:
        """
        Extract a single column definition.
        Args:
            item_def: ItemDef XML element
            item_ref: ItemRef XML element
        Returns:
            Dict containing column metadata
        """
        column = {
            "itemOID": item_def.get('OID', ''),
            "name": item_def.get('Name', ''),
        }

        # Extract label
        desc = item_def.find('odm:Description/odm:TranslatedText', self.namespaces)
        column["label"] = desc.text if desc is not None else column["name"]

        # Map ODM data types to Dataset-JSON data types
        odm_data_type = item_def.get('DataType', 'text')
        column["dataType"] = self._map_data_type(odm_data_type)

        # Extract optional attributes
        length = item_def.get('Length')
        if length:
            column["length"] = int(length)

        # Extract DisplayFormat using detected def namespace
        def_ns = self.namespaces.get('def', '')
        if def_ns:
            display_format = item_def.get(f'{def_ns}DisplayFormat')
            if display_format:
                column["displayFormat"] = display_format

        key_sequence = item_ref.get('KeySequence')
        if key_sequence:
            column["keySequence"] = int(key_sequence)

        return column

    @staticmethod
    def _map_data_type(odm_type: str) -> str:
        """
        Map ODM data type to Dataset-JSON data type.
        Args:
            odm_type: ODM data type string
        Returns:
            Dataset-JSON data type string
        """
        # Text-like types map to string
        text_types = {
            'text', 'datetime', 'date', 'time',
            'partialDate', 'partialTime', 'partialDatetime',
            'incompleteDatetime', 'durationDatetime'
        }

        if odm_type in text_types:
            return "string"
        elif odm_type == 'integer':
            return "integer"
        elif odm_type == 'float':
            return "double"
        else:
            logger.warning(f"Unknown ODM data type: {odm_type}, defaulting to string")
            return "string"

    def _create_minimal_metadata(
        self,
        dataset_name: str,
        num_rows: int,
        creation_datetime: str
    ) -> Dict:
        """
        Create minimal metadata structure when Define-XML is not available.
        The columns array will be populated later from the source data.
        Args:
            dataset_name: Name of the dataset
            num_rows: Number of rows in the dataset
            creation_datetime: ISO format creation datetime
        Returns:
            Dict containing minimal Dataset-JSON metadata
        """

        return {
            "datasetJSONCreationDateTime": creation_datetime,
            "datasetJSONVersion": "1.1.0",
            "itemGroupOID": f"IG.{dataset_name}",
            "records": num_rows,
            "name": dataset_name,
            "label": dataset_name,
            "columns": []  # will be populated from source data
        }

    def infer_columns_from_data(
        self,
        column_names: List[str],
        dataset_name: str,
        column_labels: Optional[Dict[str, str]] = None,
        column_types: Optional[Dict[str, str]] = None,
        sample_data: Optional[Dict[str, any]] = None
    ) -> List[Dict]:
        """
        Infer column definitions from source dataset metadata and data.
        Args:
            column_names: List of column names from the dataset
            column_labels: Optional dict mapping column names to labels
            column_types: Optional dict mapping column names to data types
            sample_data: Optional dict with sample values for type inference
        Returns:
            List of column definition dictionaries
        """
        columns = []

        for i, col_name in enumerate(column_names):
            column = {
                "itemOID": f"IT.{dataset_name}.{col_name}",
                "name": col_name,
                "label": column_labels.get(col_name, col_name) if column_labels else col_name,
            }

            # Determine data type
            if column_types and col_name in column_types:
                # Use provided type mapping
                column["dataType"] = self._map_pyreadstat_type(column_types[col_name])
            elif sample_data and col_name in sample_data:
                # Infer from sample data
                column["dataType"] = infer_data_type(sample_data[col_name])
            else:
                # Default to string
                column["dataType"] = "string"

            columns.append(column)

        logger.debug(f"Inferred {len(columns)} column definitions from data")
        return columns

    @staticmethod
    def _map_pyreadstat_type(pyreadstat_type: str) -> str:
        """
        Map pyreadstat variable type to Dataset-JSON data type.
        Args:
            pyreadstat_type: Variable type from pyreadstat metadata
        Returns:
            Dataset-JSON data type string
        """
        # pyreadstat uses 'numeric' and 'character'
        if 'char' in pyreadstat_type.lower() or 'str' in pyreadstat_type.lower():
            return "string"
        elif 'int' in pyreadstat_type.lower():
            return "integer"
        else:
            return "double"  # Default for numeric types
