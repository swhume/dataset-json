# dsjconvert

### Introduction

This dsjconvert.py program is a modification of Pierre Dostie's 
[Dataset-JSON-Python](https://github.com/dostiep/Dataset-JSON-Python) application. It transforms the
application into a CLI with a verbose mode to make the application's settings and behaviors more
transparent to aid in debugging. If these features are found useful I may suggest additions to the
original application. The features were added to help debug cases where pilot participants encountered errors
running the original application, possibly due to how the application was set up locally.

This application creates Dataset-JSON files from SAS7BDAT or XPT datasets.

This application requires a Define-XML file to provide the metadata needed for the conversion.

This application uses the included data directory as the default for reading and writing datasets.

### Command-line Parameter
The application uses the -v flag to turn on verbose mode, the -x flag to converts XPT files, and the -b flag to convert
SAS datasets. Set either the -x or -b flag, but not both.

The directories default to the data directory that's part of this repo if alternatives are not specified on the 
command-line.

optional arguments:

| Flag | Name | Description |
| ---- | ---------- | ---------------------------------- |
| -h | --help | show this help message and exit |
| -p | --dsj_path | directory containing Dataset-JSON datasets |
| -d | --define | directory and filename for the define.xml file |
| -s | --sas_path | directory containing the SAS files |
| -v | --verbose | verbose |
| -x | --xpt | Boolean that indicates XPT files should be converted |
| -b | --sas | Boolean that indicates SAS dataset files should be converted |

### Command-line Examples

The following example uses all defaults except it toggle verbose mode on (recommended when first
trying out the application). 
```
python dsjconvert.py -v
```

You may also run the program with all defaults and not include any command-line parameters. In this case the program
runs quietly, uses the ./data directory for all dataset inputs and outputs, and converts XPT files. The default settings
were created to make it easy to try out the program during the pilot.

The following example uses the default data directory for the dataset inputs and Dataset-JSON outputs. The -x flag
indicates that we're converting XPT file and the -v flag toggles verbose mode on.
```
python dsjconvert.py -v -x
```

This example uses the -d flag to add the Define-XML path and file name.
```
python dsjconvert.py -v -x -d c:\\Users\\SamHume\\temp\\dsj-python-outputs\\define.xml
```

This example uses the -p flag to set the path for the Dataset-JSON outputs
```
python dsjconvert.py -v -x -p c:\\Users\\SamHume\\temp\\dsj-python-outputs
```

This example adds the -s flag to set the directory for the dataset inputs which in this case
are XPT files since the -x flag is set.
```
python dsjconvert.py -v -x -p c:\\Users\\SamHume\\temp\\dsj-python-outputs 
    -s c:\\Users\\SamHume\\git\\dataset-json\\data
```

This example is the same as the previous example, except it uses the -b flag to indicate that 
SAS datasets are being converted instead of XPT files.
```
python dsjconvert.py -v -b -p c:\\Users\\SamHume\\temp\\dsj-python-outputs 
    -s c:\\Users\\SamHume\\git\\dataset-json\\data
```
