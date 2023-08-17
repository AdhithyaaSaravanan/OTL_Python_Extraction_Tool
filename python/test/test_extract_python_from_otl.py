import json
import os
import re
import pytest
import mock
import commslib.temp as cm
import shutil
import hashlib
import hou

# try:
#     import hou
# except ImportError:
#     # This should only happen when not running under Hython during testing
#     hou = None

import extract_python_from_otl as epfo


# If the test OTLs have been modified, the test data has to be generated again.

# Generates a dict representing the folder hierarchy along with the
# contents of all the .py scripts, but excludes the .json files.
def generate_folder_tree_dict(folder_path):

    result = {}
    if os.path.isdir(folder_path):
        items = os.listdir(folder_path)
        for item in items:
            item_path = os.path.join(folder_path, item)
            result[item] = generate_folder_tree_dict(item_path)
    elif os.path.isfile(folder_path):
        # if file is a .json file, ignore
        if ".json" in os.path.basename(folder_path):
            result = dict()
        # if file is a .json file, display the contents
        else:
            with open(folder_path, 'r') as file:
                result = {'file_contents': file.read()}
    return result


def get_relative_path(path):

    # Go back 3 directories to get the project name
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    project_name = os.path.basename(project_dir)

    project_dir = os.path.join(os.path.sep, project_name)
    split_path_list = path.split(project_dir)

    # path.split() splits the path into 2 strings, where the given word is specified,
    # and both exclude the given word. I then add the project directory back to the
    # 2nd string, while also removing the 1st slash of the string, to enable
    # os.path.join() to join both the strings.
    relative_path = os.path.join(project_dir, str(split_path_list[1][1:]))

    assert project_dir in relative_path

    return relative_path


def generate_relative_hda_definition_string(hda_def_str):

    # Find the index of the first separator
    first_sep_index = hda_def_str.find(os.path.sep)

    if first_sep_index != -1:
        hda_def_path = hda_def_str[:first_sep_index + 1]
        abs_path = hda_def_str[first_sep_index + 1:]
    else:
        hda_def_path = ""
        abs_path = hda_def_str

    hda_def_path = hda_def_path[:-1]

    new_hda_def_str = hda_def_path + get_relative_path(abs_path)
    return new_hda_def_str


def hash_side_effect(file_definition_str):
    """
        Generates a unique hash for the input.

        input for otl folder name hash = string of file path of otl
        input for hda folder name hash = definition of hda

        :param file_definition_str: either a str(file path of an otl) or a hda definition
        :return: a hash key
        """

    # if file_definition_str is an HDA definition
    if file_definition_str[:18] == "<hou.HDADefinition":
        file_definition_str = generate_relative_hda_definition_string(file_definition_str)
    # if file_definition_str is an OTL file path
    else:
        file_definition_str = get_relative_path(file_definition_str)

    a = hashlib.md5()
    a.update(file_definition_str)
    hash_key = a.hexdigest()
    return str(hash_key)


# gets path to ./extract-python-from-otl/test_data
def get_test_data_dir():

    script_path = os.path.abspath(__file__)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
    test_data_dir = os.path.join(base_dir, "test_data")
    return test_data_dir


# gets path to ./extract-python-from-otl/test_data/test_otls/"string variable"
def get_test_otls_paths(string):

    file_path = os.path.join(get_test_data_dir(), "test_otls", string)

    # if it's a text file with a list of otl file paths.
    if ".txt" in string:
        # access individual paths from .txt file
        with open(file_path, 'r') as file_obj:
            file_contents = file_obj.read()
            otl_file_paths = file_contents.split()
            return otl_file_paths

    # If it's just a single otl file path
    else:
        return [file_path]


# gets path to ./extract-python-from-otl/test_data_and_results/comparison_data
def get_file_path_to_test_json_files():

    results_dir = os.path.join(get_test_data_dir(), "comparison_data")
    return results_dir


def is_valid_datetime(input_str):
    datetime_pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+$')
    match = datetime_pattern.match(input_str)
    return bool(match)


def is_valid_format(input_str):
    # Context has a version number
    if "::" in input_str:
        format_pattern = re.compile(r'^\w+/\w+::\d+$')
    # Doesn't have a version number
    else:
        format_pattern = re.compile(r'^\w+/\w+$')
    match = format_pattern.match(input_str)
    return bool(match)


def assert_json_file(file_path):
    dir_contents = os.listdir(file_path)
    for file_or_dir in dir_contents:
        if os.path.isfile(os.path.join(file_path, file_or_dir)) and file_or_dir == "log.json":
            with open(os.path.join(file_path, file_or_dir), "r") as file_obj:
                json_data = json.load(file_obj)
            for key in json_data.keys():
                # log file on the otl folder directory
                if type(json_data[key]) == dict:
                    assert json_data[key]["last_mod_time"]
                    assert json_data[key]["file_path"]
                    assert is_valid_datetime(json_data[key]["last_mod_time"])
                    assert os.path.exists(json_data[key]["file_path"])

                # log file on the hda folder directory
                else:
                    for folder_dir in dir_contents:
                        if folder_dir != "log.json":
                            assert json_data[folder_dir]
                            assert is_valid_format(json_data[folder_dir])

        if os.path.isdir(os.path.join(file_path, file_or_dir)):
            folder = os.path.join(file_path, file_or_dir)
            assert_json_file(folder)



@pytest.mark.parametrize(
    'file_paths',
    [
        pytest.param([get_test_otls_paths("sky_scraper.hda")[0]]),
        pytest.param([])
    ]
)
def test_del_folder_count(file_paths):
    with mock.patch("__builtin__.open", mock.mock_open(read_data="mocked_data")), \
            mock.patch("extract_python_from_otl.extract_py_from_hda"), \
            mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"), \
            mock.patch("json.load"), mock.patch("json.dumps"), \
            mock.patch("shutil.rmtree") as del_folder:

        path_exists.return_value = True

        scripts_folder_path = "/tmp"
        epfo.extract_py_from_otl(file_paths, scripts_folder_path)

    if len(file_paths) == 0:
        assert del_folder.call_count == 0


@pytest.mark.parametrize(
    'var',
    [
        pytest.param("1"),
        pytest.param("a"),
        pytest.param(str(get_test_otls_paths("sky_scraper")[0])),
        pytest.param(str(hou.hda.definitionsInFile(get_test_otls_paths("sky_scraper.hda")[0])[0]))
    ]
)
def test_get_hash(var):
    result = epfo.get_hash(var)
    assert result is not None
    assert isinstance(result, str)
    regex = re.compile(r"^[a-f0-9]+$")
    assert regex.match(result)


@pytest.mark.parametrize(
    ('scripts_folder_name', 'file_name', 'expected_script'),
    [
        pytest.param("/main_python_scripts", "/PythonModule.py", 'print("Python script")'),
        pytest.param("/main_python_scripts", "/OnCreated.py", 'print("onCreated")'),
        pytest.param("/main_python_scripts", "/OnUpdated.py", 'print("onUpdated")'),
        pytest.param("/parameter_callbacks", "/button.py", 'print("callback")'),
        pytest.param("/item_generation_scripts", "/button.py", """result = []
for i in xrange(13):
    value = chr(2*i+65)+chr(2*i+66)
    result.append(value)
    result.append(value)

return result"""),
    ]
)
def test_extract_py_and_write(scripts_folder_name, file_name, expected_script):
    file_path = get_test_otls_paths("sky_scraper.hda")[0]
    definition = hou.hda.definitionsInFile(file_path)[0]
    temp_folder_name = "otl_python_extraction_tool_test"
    temp_folder_path = cm.make_directory(temp_folder_name)

    assert temp_folder_name in temp_folder_path

    hou.hda.installFile(file_path)

    epfo.extract_py_and_write(definition, temp_folder_path)

    script_file_path = temp_folder_path + scripts_folder_name + file_name
    with open(script_file_path, 'r') as file_obj:
        content = file_obj.read()
        assert content == expected_script

    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)


@pytest.mark.parametrize(
    ('parm_template', 'expected'),
    [
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         script_callback="print 'hello'",
                                         script_callback_language=hou.scriptLanguage.Python),
                     {"/tmp/parameter_callbacks/test_int.py": "print 'hello'"}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="print 'hello'",
                                         item_generator_script_language=hou.scriptLanguage.Python), {}),
        pytest.param(hou.FloatParmTemplate("test_int", "Test Int", 1,
                                           script_callback="print 'hello'",
                                           script_callback_language=hou.scriptLanguage.Hscript), {}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="",
                                         item_generator_script_language=hou.scriptLanguage.Python), {}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="print 'hello'",
                                         item_generator_script_language=hou.scriptLanguage.Hscript), {}),
    ]
)
def test_extract_parameter_callbacks(parm_template, expected):
    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"):
        path_exists.return_value = False

        hda_folder_path = "/tmp"
        result = epfo.extract_parameter_callbacks(hda_folder_path, parm_template)
        assert result == expected


@pytest.mark.parametrize(
    ('parm_template', 'expected'),
    [
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         script_callback="print 'hello'",
                                         script_callback_language=hou.scriptLanguage.Python), {}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="print 'hello'",
                                         item_generator_script_language=hou.scriptLanguage.Python),
                     {"/tmp/item_generation_scripts/test_int.py": "print 'hello'"}),
        pytest.param(hou.FloatParmTemplate("test_int", "Test Int", 1,
                                           script_callback="print 'hello'",
                                           script_callback_language=hou.scriptLanguage.Python), {}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="",
                                         item_generator_script_language=hou.scriptLanguage.Python), {}),
        pytest.param(hou.IntParmTemplate("test_int", "Test Int", 1,
                                         item_generator_script="print 'hello'",
                                         item_generator_script_language=hou.scriptLanguage.Hscript), {}),
    ]
)
def test_extract_item_generation_scripts(parm_template, expected):
    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"):
        path_exists.return_value = False

        hda_folder_path = "/tmp"
        result = epfo.extract_item_generation_scripts(hda_folder_path, parm_template)
        assert result == expected


@pytest.mark.parametrize(
    ('definition', 'file_names', 'expected_scripts'),
    [
        pytest.param(hou.hda.definitionsInFile(get_test_otls_paths("sky_scraper.hda")[0])[0],
                     ['/OnCreated.py', '/OnUpdated.py', '/PythonModule.py'],
                     ['print("onCreated")', 'print("onUpdated")', 'print("Python script")'])
    ]
)
def test_extract_py_scripts(definition, file_names, expected_scripts):
    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"):
        path_exists.return_value = False

        hda_folder_path = "/tmp"
        general_file_path = hda_folder_path + "/main_python_scripts"

        # prepare the keys / file paths of the result dict
        file_paths = []
        for file_name in file_names:
            file_paths.append(general_file_path + file_name)

        # initial and make expected result dict
        expected_result_dict = dict()
        for file_path in file_paths:
            expected_result_dict.update({file_path: expected_scripts[file_paths.index(file_path)]})

        result = epfo.extract_py_scripts(definition, hda_folder_path)
        assert result == expected_result_dict


@pytest.mark.parametrize(
    "otl_file_paths",
    [
        pytest.param(get_test_otls_paths("sky_scraper.hda")),
        pytest.param(get_test_otls_paths("otl_list.txt")),
        pytest.param([])
    ]
)
def test_json_files(otl_file_paths):

    temp_folder_name = "otl_python_extraction_tool_json_test"
    temp_folder_path = cm.make_directory(temp_folder_name)
    assert temp_folder_name in temp_folder_path

    folder_name = "otl_scripts_folder"

    epfo.extract_python(otl_file_paths, temp_folder_path, folder_name)

    # check if the log.json files are correctly formatted
    assert_json_file(temp_folder_path)

    # get current tool generated folder structure in a dictionary
    #folder_tree_dict = generate_folder_tree_dict(temp_folder_path)
    #print(json.dumps(folder_tree_dict, indent=4))

    # clean up
    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)


@pytest.mark.parametrize(
    "test_data",
    [
        pytest.param("sky_scraper.hda"),
        pytest.param("otl_list.txt"),
        pytest.param("")
    ]
)
def test_functionality(test_data):

    with mock.patch("extract_python_from_otl.get_hash", side_effect=hash_side_effect):

        test_otl_data_name = test_data
        temp_folder_name = "otl_python_extraction_tool_test"
        temp_folder_path = cm.make_directory(temp_folder_name)

        assert temp_folder_name in temp_folder_path

        folder_name = "otl_scripts_folder"

        if test_data == "":
            file_paths = []
        else:
            file_paths = get_test_otls_paths(test_data)

        # file_paths = [] if test_data is "" else get_test_otls_paths(test_data)

        epfo.extract_python(file_paths, temp_folder_path, folder_name)

    # If input is a txt file, name the .json file "multiple_otls"
    if ".txt" in test_data:
        test_otl_data_name = "multiple_otls.json"
    # If it's a single otl, name it "sky_scraper_otl"
    elif "sky_scraper" in test_data:
        test_otl_data_name = "sky_scraper_otl.json"

    # get expected data
    if test_data == "":
        expected_data = {'otl_scripts_folder': {'log.json': {}}}
    else:
        test_json_file_path = os.path.join(get_file_path_to_test_json_files(), test_otl_data_name)
        with open(test_json_file_path, "r") as file_obj:
            expected_data = json.load(file_obj)

    # get current tool generated folder structure in a dictionary
    folder_tree_dict = generate_folder_tree_dict(temp_folder_path)

    # compare both the data
    assert folder_tree_dict == expected_data

    # clean up
    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)
