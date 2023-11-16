import json
import os
import re
import pytest
import mock
import commslib.temp as cm
import shutil
import hashlib
import hou
import extract_python_from_otl as epfo

# If the test OTLs have been modified, the test data has to be generated again.


def generate_folder_tree_dict(folder_path):
    """
    Takes in a folder path and returns a dictionary depicting the folder structure
    along with the file contents, but excludes json file contents.

    :param str folder_path: Folder path to be analysed and displayed
    :return: dict result: Dictionary representing the folder structure of the input folder path
    """

    result = {}
    if os.path.isdir(folder_path):
        items = os.listdir(folder_path)
        for item in items:
            item_path = os.path.join(folder_path, item)
            result[item] = generate_folder_tree_dict(item_path)
    elif os.path.isfile(folder_path):
        # if file is a .json file, ignore
        if os.path.basename(folder_path).endswith(".json"):
            result = dict()
        # if file is a .py file, display the contents
        else:
            with open(folder_path, 'r') as file:
                result = {'file_contents': file.read()}
    return result


def get_tool_project_dir():
    """
    Gets the project directory of the tool
    :return: str project directory of the tool
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def get_relative_path_from_project_dir(abs_path):
    """
    Gets the relative path from the input absolute path with the project directory
    as the root directory.

    :param str abs_path: absolute path of otl
    :return: str Relative path.
    """
    return os.path.relpath(abs_path, os.path.dirname(get_tool_project_dir()))


def generate_relative_hda_definition_string(hda_def_str):
    """
    Changes the absolute path in an hda definition to a relative path
    with the project directory as the root directory.

    :param str hda_def_str: str(hda definition)
    :return: str Relative path.
    """

    # Find the index of the first separator
    first_sep_index = hda_def_str.find(os.path.sep)

    if first_sep_index != -1:
        hda_def_path = hda_def_str[:first_sep_index + 1]
        abs_path = hda_def_str[first_sep_index + 1:]
    else:
        hda_def_path = ""
        abs_path = hda_def_str

    hda_def_path = hda_def_path[:-1]

    new_hda_def_str = hda_def_path + get_relative_path_from_project_dir(abs_path)
    return new_hda_def_str


def hash_side_effect(file_definition_str):
    """
        Generates a unique hash for the input.

        input for otl folder name hash = file path of otl
        input for hda folder name hash = str(definition of hda)

        :param str file_definition_str: file path of an otl or a str(hda definition)
        :return: a hash key
        """

    # if file_definition_str is an HDA definition
    if file_definition_str.startswith("<hou.HDADefinition"):
        file_definition_str = generate_relative_hda_definition_string(file_definition_str)
    # if file_definition_str is an OTL file path
    else:
        file_definition_str = get_relative_path_from_project_dir(file_definition_str)

    a = hashlib.md5()
    a.update(file_definition_str)
    hash_key = a.hexdigest()
    return str(hash_key)


def get_test_data_dir():
    """
    Gets the path to ~/extract-python-from-otl/test_data
    :return: str test_data_dir: ~/extract-python-from-otl/test_data
    """
    return os.path.join(get_tool_project_dir(), "test_data")


def get_sky_scraper_otl_path():
    """
    Gets the path to ~/extract-python-from-otl/test_data/test_otls/sky_scraper.hda
    :return: str test_data_dir: ~/extract-python-from-otl/test_data/test_otls/sky_scraper.hda
    """
    return os.path.join(get_test_data_dir(), os.path.join("test_otls", "sky_scraper.hda"))


def get_test_otls_paths():

    file_path = os.path.join(get_test_data_dir(), os.path.join("test_otls", "otl_list.txt"))
    with open(file_path, 'r') as file_obj:
        file_contents = file_obj.read()
        otl_file_paths = file_contents.split()
        return otl_file_paths


def get_comparison_data_dir():
    """
    Gets the path to ~/extract-python-from-otl/test_data/comparison_data
    :return: str results_dir: ~/extract-python-from-otl/test_data/comparison_data
    """
    return os.path.join(get_test_data_dir(), "comparison_data")


def is_valid_datetime(input_str):
    """
    Checks if the input string represents a date and time.

    :param str input_str: date and time
    :return: bool
    """
    datetime_pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+$')
    match = datetime_pattern.match(input_str)
    return match is not None


def assert_json_file(file_path):
    """
    Checks whether the log.json files in the given folder tree contains all the
    appropriate keys and values.

    :param str file_path: Parent directory of otl_scripts_folder
    """

    dir_contents = os.listdir(file_path)
    for file_or_dir in dir_contents:
        file_or_dir_path = os.path.join(file_path, file_or_dir)
        if os.path.isfile(file_or_dir_path) and file_or_dir == "log.json":
            with open(file_or_dir_path, "r") as file_obj:
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

        if os.path.isdir(os.path.join(file_path, file_or_dir)):
            folder = os.path.join(file_path, file_or_dir)
            assert_json_file(folder)


@pytest.mark.parametrize(
    'file_paths',
    [
        pytest.param(get_test_otls_paths()),
        pytest.param([])
    ]
)
def test_del_folder_count(file_paths):
    """
    Tests and asserts the appropriate usage of shutil.rmtree()
    :param list file_paths: otl file path(s) (Tool function input)
    """

    with mock.patch("__builtin__.open", mock.mock_open(read_data="mocked_data")), \
            mock.patch("extract_python_from_otl.extract_py_from_hda"), \
            mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"), \
            mock.patch("json.load"), mock.patch("json.dump"), \
            mock.patch("shutil.rmtree") as del_folder:

        path_exists.return_value = True

        scripts_folder_path = "/tmp"
        print(file_paths)
        epfo.extract_py_from_otl(file_paths, scripts_folder_path)

    if len(file_paths) == 0:
        assert del_folder.call_count == 0


@pytest.mark.parametrize(
    'file_definition_str',
    [
        pytest.param("1"),
        pytest.param("a"),
        pytest.param(str(get_sky_scraper_otl_path())),
        pytest.param(str(hou.hda.definitionsInFile(get_sky_scraper_otl_path())[0]))
    ]
)
def test_get_hash(file_definition_str):
    """
    Asserts the composition of the return value of the get hash function

    :param str file_definition_str: otl file path or str(hda definition)
    """

    result = epfo.get_hash(file_definition_str)
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
    """
    Tests the return value of extract_py_and_write()

    :param str scripts_folder_name: Name of the generated scripts folder
    :param str file_name: Expected script file name
    :param str expected_script: Expected script
    """

    file_path = get_sky_scraper_otl_path()
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
    """
    Checks the return value of extract_parameter_callbacks()

    :param <hou.ParmTemplate> parm_template: Tool function input
    :param dict expected: Expected result
    """
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
    """
    Checks the return value of extract_item_generation_scripts()

    :param <hou.ParmTemplate> parm_template: Tool function input
    :param dict expected: Expected result
    """

    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir"):
        path_exists.return_value = False

        hda_folder_path = "/tmp"
        result = epfo.extract_item_generation_scripts(hda_folder_path, parm_template)
        assert result == expected


@pytest.mark.parametrize(
    ('definition', 'file_names', 'expected_scripts'),
    [
        pytest.param(hou.hda.definitionsInFile(get_sky_scraper_otl_path())[0],
                     ['/OnCreated.py', '/OnUpdated.py', '/PythonModule.py'],
                     ['print("onCreated")', 'print("onUpdated")', 'print("Python script")'])
    ]
)
def test_extract_py_scripts(definition, file_names, expected_scripts):
    """
    Checks the return value of extract_py_scripts()

    :param <hou.HDADefinition> definition: hda definition (Tool function input)
    :param list file_names: List of expected script file names
    :param list expected_scripts: List of expected scripts
    """
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
        pytest.param([get_sky_scraper_otl_path()]),
        pytest.param(get_test_otls_paths()),
        pytest.param([])
    ]
)
def test_json_files(otl_file_paths):
    """
    Checks the contents of the loh.json files in the generated folder tree.

    :param list otl_file_paths: List of otl file path(s) (Tool function input)
    """

    temp_folder_name = "otl_python_extraction_tool_json_test"
    temp_folder_path = cm.make_directory(temp_folder_name)
    assert temp_folder_name in temp_folder_path

    folder_name = "otl_scripts_folder"

    epfo.extract_python(otl_file_paths, temp_folder_path, folder_name)

    # check if the log.json files are correctly formatted
    assert_json_file(temp_folder_path)

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
    """
    Integration test for the entire tool - Checks the hierarchy / structure
    of the generated scripts folder. Also checks the contents of all the
    files inside, excluding the log.json files.

    :param str test_data: name of the test data (an otl or a text file
                            containing a list of otl file paths.)
    """

    with mock.patch("extract_python_from_otl.get_hash", side_effect=hash_side_effect):

        test_otl_data_name = test_data
        temp_folder_name = "otl_python_extraction_tool_test"
        temp_folder_path = cm.make_directory(temp_folder_name)

        assert temp_folder_name in temp_folder_path

        folder_name = "otl_scripts_folder"

        if test_data == "":
            file_paths = []
        elif test_data == "sky_scraper.hda":
            file_paths = [get_sky_scraper_otl_path()]
        elif test_data == "otl_list.txt":
            file_paths = get_test_otls_paths()

        epfo.extract_python(file_paths, temp_folder_path, folder_name)

    # If input is a txt file, name the .json file "multiple_otls"
    if test_data.endswith(".txt"):
        test_otl_data_name = "multiple_otls.json"
    # If it's a single otl, name it "sky_scraper_otl"
    elif "sky_scraper" in test_data:
        test_otl_data_name = "sky_scraper_otl.json"

    # get expected data
    if test_data == "":
        expected_data = {'otl_scripts_folder': {'log.json': {}}}
    else:
        test_json_file_path = os.path.join(get_comparison_data_dir(), test_otl_data_name)
        with open(test_json_file_path, "r") as file_obj:
            expected_data = json.load(file_obj)

    # get current tool generated folder structure in a dictionary
    folder_tree_dict = generate_folder_tree_dict(temp_folder_path)

    # compare both the data
    assert folder_tree_dict == expected_data

    # clean up
    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)
