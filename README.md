# Extract Python From OTLs / HDAs

## Summary:

The tool processes a list .hda(houdini digital assets) files or otls (operator type libraries), 
and extracts the python scripts within them into a simple folder tree on disk.

## Steps to use:
### Running the tool:

1. Run `go comms`
2. Go to the tool project directory and run `module load ./extract_python_from_otls.module`
3. Run `extract_python_from_otl` to use the tool (Tool arguments can be found below)

Default folder name is "otl_python_scripts".

Default directory is the current working directory.

### Running tests:

1. Run `module load extract_python_from_otls_test.module`. This should automatically module load `comms-pipeline` and `pythonessentials-devel/2.7`
2. Navigate to `python/test/` and run `hython -m pytest ./test_extract_python_from_otl.py` to run the tests.

The tests use the test otls that are present in `test_data/test_otls/`.
The integration test reads data from the json files present in `test_data/comparison_data/`.
To generate the comparison data again: `test/generate_test_results.py` can be run.


## Arguments:
```
 -f,	   --otl_paths_file, 	 A file containing a list of OTL pathways.
 -o, 	   --otl, 	         An OTL or multiple OTLS.
 -n,       --name,               Name of the generated scripts folder.
 -d,       --output_directory,   Parent directory of the generated scripts folder.
```

## Folder Structure:

The tool generates a folder containing the scripts in the following template folder structure:

### Template Folder Tree:
       
```
-- otl_scripts_folder
    |-- log.json
    `-- file_name_hash
        |-- log.json
        `-- asset_name_hash
            |-- item_generation_scripts
            |   `-- scripts
            |-- main_python_scripts
            |   |-- log.json
            |   |-- scripts
            `-- parameter_callbacks
                `-- scripts
```
 
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
            |   |-- log.json
            |   |-- OnCreated_e50fe1fa62822bf5f8c9b37d9c1fbc3f.py
            |   |-- OnDeleted_3eec1e8a7193634a1b2e62c514bae604.py
            |   |-- OnUpdated_d32f49ced40ea32088eab01919062ec1.py
            |   |-- PythonModule_211dd2fe2199e4fae008f03322086ecb.py
            |   |-- test_1_4e70ffa82fbe886e3c4ac00ac374c29b.py
            |   `-- test_1_9a7b64c98b066602b21f869ae7cd673a.py
            `-- parameter_callbacks
                `-- button.py
```

## Log files:

### log.json on the files folder directory

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

### log.json on the assets folder directory

#### Example:

```
{
    "sky_scraper_c5afa8fc0b39c9ef01f1db5199a69b52": "Object/sky_scraper"
}
```

### log.json on the main_python_scripts directory

#### Example:

```
{
  "OnDeleted_3eec1e8a7193634a1b2e62c514bae604.py": "OnDeleted", 
  "OnUpdated_d32f49ced40ea32088eab01919062ec1.py": "OnUpdated", 
  "test_1_4e70ffa82fbe886e3c4ac00ac374c29b.py": "test_1", 
  "PythonModule_211dd2fe2199e4fae008f03322086ecb.py": "PythonModule", 
  "test_1_9a7b64c98b066602b21f869ae7cd673a.py": "test 1", 
  "OnCreated_e50fe1fa62822bf5f8c9b37d9c1fbc3f.py": "OnCreated"
}
```
