import argparse
import os
import pandas as pd
import pyreadstat
import saxonche
import datetime
import json
import jsonschema


# Datetime to Integer Function
def datetime_to_integer(dt):
    if isinstance(dt, datetime.date):
        # For date objects, convert to SAS date representation
        days_since_epoch = (dt - datetime.date(1960, 1, 1)).days
        return days_since_epoch
    elif isinstance(dt, datetime.datetime):
        # For datetime objects, convert to SAS date representation
        days_since_epoch = (dt.date() - datetime.date(1960, 1, 1)).days
        seconds_since_midnight = (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6)
        return days_since_epoch + seconds_since_midnight / 86400
    elif isinstance(dt, datetime.time):
        # For time objects, convert to SAS date representation (time-only)
        seconds_since_midnight = (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6)
        return seconds_since_midnight / 86400


def set_cmd_line_args():
    parser = argparse.ArgumentParser(description="dsjconvert optional command-line parameters - parameters have defaults")
    parser.add_argument("-p", "--dsj_path", help="directory containing Dataset-JSON datasets", required=False,
                        dest="dsj_path", default=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data'))
    parser.add_argument("-d", "--define", help="directory and filename for the define.xml file", required=False,
                        dest="define_file", default=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'define.xml'))
    parser.add_argument("-s", "--sas_path", help="directory containing the SAS files", required=False,
                        dest="sas_path", default=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data'))
    parser.add_argument("-v", "--verbose", help="verbose", required=False, dest="verbose",
                        action='store_true')
    parser.add_argument("-x", "--xpt", help="Boolean that indicates XPT files should be processed (default)", required=False,
                        dest="is_xpt", action='store_true')
    parser.add_argument("-b", "--sas", help="Boolean that indicates SAS dataset files should be processed", required=False,
                        dest="is_sas", action='store_true')
    args = parser.parse_args()
    return args


def main():
    args = set_cmd_line_args()
    base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    if not (args.is_xpt or args.is_sas):
        args.is_xpt = True
    if args.verbose:
        print(f"current path: {base_path}")
        print(f"define.xml: {args.define_file}")
        print(f"SAS datasets path: {args.sas_path}")
        print(f"Dataset-JSON output path: {args.dsj_path}")
        if args.is_xpt:
            print("converting XPT files...")
        else:
            print("converting SAS datasets...")

    if any((args.define_file == "", args.sas_path == "", args.dsj_path == "")):
        raise Exception("Please use the required command-line arguments")

    # Check if Dataset-JSON stylesheet exists where it should.
    elif not (os.path.isfile(os.path.join(base_path, "stylesheet", "Dataset-JSON.xsl"))):
        raise Exception("Stylesheet Dataset-JSON.xsl file not found. Make sure it is located in a subfolder Stylesheet.")

    # Check if Dataset-JSON schema exists where it should.
    elif not (os.path.isfile(os.path.join(base_path, "schema", "dataset.schema.json"))):
        raise Exception("Schema dataset.schema.json file not found. Make sure it is located in a subfolder Schema.")

    # Create Dataset-JSON files
    else:

        # Load Dataset-JSON Schema
        with open(os.path.join(base_path, "schema", "dataset.schema.json")) as schemajson:
            schema = schemajson.read()
        schema = json.loads(schema)

        # Initialize list of files either not JSON compliant with nor compliant with Dataset-JSON schema
        error_files = []

        # Build JSON files from SAS/XPT datasets
        files = [file for file in os.listdir(args.sas_path) if file.endswith(".sas7bdat")] \
                    if not args.is_xpt else [file for file in os.listdir(args.sas_path)
                    if file.endswith(".xpt")] if args.is_xpt else []

        if files:
            for file_count, file in enumerate(files, 1):
                # Extract data and metadata from either SAS or XPT datasets
                if args.verbose:
                    print(f"converting file {file_count}: {os.path.join(args.sas_path, file)}")
                if args.is_sas:
                    try:
                        df, meta = pyreadstat.read_sas7bdat(os.path.join(args.sas_path, file))
                    except UnicodeDecodeError as ex:
                        print(f"Unable to convert {os.path.join(args.sas_path, file)}.\nMessage: {ex}")
                        continue
                elif args.is_xpt:
                    try:
                        df, meta = pyreadstat.read_xport(os.path.join(args.sas_path, file), encoding="WINDOWS-1252")
                    except UnicodeDecodeError as ex:
                        print(f"Unable to convert {os.path.join(args.sas_path, file)}.\nMessage: {ex}")
                        continue

                dsname = file.upper().rsplit('.', 1)[0]

                # Extract Dataset-JSON metadata from Define.xml
                processor = saxonche.PySaxonProcessor(license=False)
                xslt = processor.new_xslt30_processor()
                xslt.set_parameter("dsName", processor.make_string_value(dsname))
                xslt.set_parameter("creationDateTime", processor.make_string_value(
                    datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
                xslt.set_parameter("nbRows", processor.make_integer_value(meta.number_rows))
                result = xslt.transform_to_string(source_file=args.define_file,
                                                  stylesheet_file=os.path.join(base_path, "stylesheet", "Dataset-JSON.xsl"))
                json_data = json.loads(result)

                if "clinicalData" in json_data:
                    data_key = "clinicalData"
                elif "referenceData" in json_data:
                    data_key = "referenceData"

                items = json_data[data_key]["itemGroupData"][dsname]["items"]

                pairs = {item["name"]: item["type"] for item in items if item["name"] != "ITEMGROUPDATASEQ"}

                if sorted([col.upper() for col in df.columns.tolist()]) == sorted(
                        [item["name"].upper() for item in items if item["name"] != "ITEMGROUPDATASEQ"]):

                    # Extract Dataset-JSON data from each SAS or XPT datasets
                    records = ''
                    if meta.number_rows > 0:
                        for index, row in df.iterrows():
                            if index > 0:
                                records += ','
                            records += '[' + str(index + 1)
                            for column in df.columns:
                                type = pairs[column]
                                value = row[column]
                                records += ','
                                if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
                                    records += str(datetime_to_integer(value))
                                elif type == "string":
                                    records += json.dumps(value)
                                elif type == "integer":
                                    if pd.isna(value):
                                        records += "null"
                                    elif value == "":
                                        records += "null"
                                    else:
                                        # records += str(int(value))
                                        records += json.dumps(int(value))
                                else:
                                    if pd.isna(value):
                                        records += "null"
                                    else:
                                        # records += str(value)
                                        records += json.dumps(value)
                            records += ']'

                    json_data[data_key]["itemGroupData"][dsname]["itemData"] = json.loads("[" + records + "]")

                    # Check if JSON file is valid against the Dataset-JSON schema
                    error = False
                    try:
                        jsonschema.validate(json_data, schema)
                    except:
                        error = True

                    # Save Dataset-JSON files
                    if not error:
                        try:
                            with open(os.path.join(args.dsj_path, dsname) + ".json", "w") as json_file:
                                json.dump(json_data, json_file)
                        except:
                            error = True

                    # Add the SAS or XPT files that are not compliant with either JSON or Dataset-JSON schema
                    if error:
                        error_files.append(file)


                else:
                    error_files.append(file)

            # Pop-up an error window listing all files that are not compliant with either JSON or Dataset-JSON schema
            if error_files:
                msgfiles = '\n'.join(error_files)
                raise Exception(f"The following JSON files are either not compliant with Dataset-JSON schema or "
                                f"dataset contents is not aligned with Define.xml metadata: {msgfiles}\n")

            # Pop-up when all files are compliant with Dataset-JSON standard
            else:
                if args.verbose:
                    print(f"Dataset-JSON files created in {args.dsj_path}")
        else:
            raise Exception(f"No datasets found in the directory {args.sas_path}")


if __name__ == '__main__':
    main()


