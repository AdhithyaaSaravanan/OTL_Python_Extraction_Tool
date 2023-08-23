# Extract Python From OTLs

## Summary:

The tool processes a list .hda(houdini digital assets) files or otls (operator type libraries), 
and extracts the python scripts within them into a simple folder tree on disk.

## Steps to use:
### Running the tool:

1. Run `module load extract_python_from_otls.module`
2. Navigate to `bin` and run `extract_python_from_otl` to use the tool (Tool arguments can be found below)

### Running tests:

1. Run `module load extract_python_from_otls_test.module`. This should automatically module load `comms-pipeline` and `pythonessentials-devel/2.7`
2. Navigate to `python/test/` and run `hython -m pytest ./test_extract_python_from_otl.py` to run the tests.

The tests use the test otls that are present in `test_data/test_otls/`.
The integration test reads data from the json files present in `test_data/comparison_data/`.
To generate the comparison data again: `test/generate_test_results.py` can be run.


## Arguments:
```
 -f,	   –otl_paths_file, 	A file containing a list of OTL pathways.
 -o, 	   –otl, 	        An OTL or multiple OTLS.
 -n,       –name,               Name of the generated scripts folder.
 -d,       –output_directory,   Parent directory of the generated scripts folder.
```

## Folder Structure:

The tool generates a folder containing the scripts in the following template folder structure:

### Template Folder Tree:
 
 - otl_python_scripts
   - log.json
   - otl_filename_hash
     - log.json
     - hda_filename_hash
       - Main_python_scripts
         - scripts
       - Item_generator_scripts
         - scripts
       - Parameter_callback_scripts
         - scripts
 
### Example:
       
```
-- otl_scripts_folder
    |-- log.json
    `-- sky_scraper_hda_af594ebcf7ba6f780d2333aaa5aefef1
        |-- log.json
        `-- sky_scraper_c5afa8fc0b39c9ef01f1db5199a69b52
            |-- item_generation_scripts
            |   `-- button.py
            |-- main_python_scripts
            |   |-- OnCreated.py
            |   |-- OnUpdated.py
            |   `-- PythonModule.py
            `-- parameter_callbacks
                `-- button.py
```


### Output Folder:

The folder can contain multiple folders corresponding to multiple otls, each containing multiple HDAs. Both the OTL 
and HDA names are hashed, ensuring unique identifiers to prevent naming conflicts. 
The log.json file holds the hash keys and file directories for each specific file name.
Both the OTL and HDA directories have this log file. Additionally, the log file in the 
OTL directory records the last modification time of all the OTLs, aiding in handling 
multiple script runs.The corresponding folders inside the HDA folders are only created 
if the relevant scripts are found.

## Log files:

### log.json on the otl folder directory

#### Template:

```
{
    "otl_unique_name": 
        {
            "last_mod_time": otl_last_modified_time, 
            "file_path": otl_file_path
        }
}
```

#### Example:

```
{
    "sky_scraper_hda_af594ebcf7ba6f780d2333aaa5aefef1": 
        {
            "last_mod_time": "2023-08-04 17:13:18.829934", 
            "file_path": "Path/to/sky_scraper.hda"
        }
}
```

### log.json on the hda folder directory

#### Template:

```
{
    "hda_unique_name": Context / hda name
}
```

#### Example:

```
{
    "sky_scraper_c5afa8fc0b39c9ef01f1db5199a69b52": "Object/sky_scraper"
}
```
