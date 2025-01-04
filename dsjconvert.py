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

def read_dsj_schema(base_path):
    with open(os.path.join(base_path, "schema", "dataset.schema.json")) as dsj_schema:
        schema = dsj_schema.read()
    schema = json.loads(schema)
    return schema

def read_define_file(args, dsname, base_path, meta):
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
    return json_data


def read_source_dataset(args, file):
    df = None
    meta = None
    if args.is_sas:
        # df, meta = pyreadstat.read_sas7bdat(os.path.join(args.sas_path, file))
        df, meta = pyreadstat.read_sas7bdat(file)
    elif args.is_xpt:
        # df, meta = pyreadstat.read_xport(os.path.join(args.sas_path, file), encoding="WINDOWS-1252")
        df, meta = pyreadstat.read_xport(file, encoding="WINDOWS-1252")
    return df, meta

def convert_dataset(args, base_path, file, schema):
    error = False
    try:
        df, meta = read_source_dataset(args, os.path.join(args.sas_path, file))
    except UnicodeDecodeError as ex:
        print(f"Unable to convert {os.path.join(args.sas_path, file)}.\nMessage: {ex}")
        error = True
        return error

    dsname = file.upper().rsplit('.', 1)[0]
    json_data = read_define_file(args, dsname, base_path, meta)

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
    return error

def convert_datasets_to_dsj(args, base_path):
    schema = read_dsj_schema(base_path)
    error_files = []
    files = [file for file in os.listdir(args.sas_path) if file.endswith(".sas7bdat")] \
        if not args.is_xpt else [file for file in os.listdir(args.sas_path)
                                 if file.endswith(".xpt")] if args.is_xpt else []
    if not files:
        raise Exception(f"No datasets found to convert in path {args.sas_path}")

    for file_count, file in enumerate(files, 1):
        # Extract data and metadata from either SAS or XPT datasets
        if args.verbose:
            print(f"converting file {file_count}: {os.path.join(args.sas_path, file)}")

        is_error = convert_dataset(args, base_path, file, schema)
        # Add the SAS or XPT files that are not compliant with either JSON or Dataset-JSON schema
        if is_error:
            error_files.append(file)

        # list all files that are not valid JSON or Dataset-JSON
    if error_files:
        msgfiles = '\n'.join(error_files)
        raise Exception(f"The following JSON files are either not compliant with Dataset-JSON schema or "
                        f"dataset contents is not aligned with Define.xml metadata: {msgfiles}\n")
    else:
        if args.verbose:
            print(f"Dataset-JSON files created in {args.dsj_path}")


def main():
    args = set_cmd_line_args()
    # base_path is used to enable relative paths to be set in the cmd-line parameters
    base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    # XPT conversion is the default
    if not (args.is_xpt or args.is_sas):
        args.is_xpt = True
    # verbose mode is available to aid in debugging
    if args.verbose:
        print(f"current path: {base_path}")
        print(f"define.xml: {args.define_file}")
        print(f"SAS datasets path: {args.sas_path}")
        print(f"Dataset-JSON output path: {args.dsj_path}")
        if args.is_xpt:
            print("converting XPT files...")
        else:
            print("converting SAS datasets...")

    # TODO cmd-line args have default values set to aid in development and testing - keep defaults?
    if any((args.define_file == "", args.sas_path == "", args.dsj_path == "")):
        raise Exception("Please use the required command-line arguments")

    # check for the Dataset-JSON stylesheet existence
    elif not (os.path.isfile(os.path.join(base_path, "stylesheet", "Dataset-JSON.xsl"))):
        raise Exception("Stylesheet Dataset-JSON.xsl file not found. Make sure it is located in a subfolder Stylesheet.")

    # check for the Dataset-JSON schema existence
    elif not (os.path.isfile(os.path.join(base_path, "schema", "dataset.schema.json"))):
        raise Exception("Schema dataset.schema.json file not found. Make sure it is located in a subfolder Schema.")

    convert_datasets_to_dsj(args, base_path)

if __name__ == '__main__':
    main()


