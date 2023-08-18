import json
import os
import re
import pytest
import mock
import commslib.temp as cm
import shutil
import hashlib
import hou

# TODO: Remove commented code
# try:
#     import hou
# except ImportError:
#     # This should only happen when not running under Hython during testing
#     hou = None

import extract_python_from_otl as epfo

# If the test OTLs have been modified, the test data has to be generated again.


# Generates a dict representing the folder hierarchy along with the
# contents of all the .py scripts, but excludes the .json file contents.
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
        # TODO: use str.endswith()
        if ".json" in os.path.basename(folder_path):
            result = dict()
        # if file is a .py file, display the contents
        else:
            with open(folder_path, 'r') as file:
                result = {'file_contents': file.read()}
    return result


def get_relative_path(abs_path):
    """
    Gets the relative path from the input absolute path with the project directory
    as the root directory.

    :param str abs_path: absolute path of otl
    :return: str Relative path.
    """
    # TODO: This function lacks clarity.
    #    Problem 1) It looks very generic, but digging into it, it looks
    #      like it only works with the OTL paths that you have under the "test_otls" folder,
    #      and yet it's called a very generic name that doesn't mention OTLs at all.
    #    Problem 2) I would have expected you to use `os.path.relpath` in here somewhere, but you're
    #      falling back to old habits of calling split and trying to do list slicing to get what
    #      you're after. This is not a good way to go.
    #    I would have expected something more like this:
    #        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    #        return os.path.relpath(abs_path, project_dir)

    # Go back 3 directories to get the project name
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(abs_path)))
    project_name = os.path.basename(project_dir)

    project_dir = os.path.join(os.path.sep, project_name)
    split_path_list = abs_path.split(project_dir)

    # path.split() splits the path into 2 strings, where the given word is specified,
    # and both exclude the given word. I then add the project directory back to the
    # 2nd string, while also removing the 1st slash of the string, to enable
    # os.path.join() to join both the strings.
    relative_path = os.path.join(project_dir, str(split_path_list[1][1:]))

    # TODO: If it's a path relative to the project_dir, this should fail every time, no?
    assert project_dir in relative_path

    return relative_path


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

    new_hda_def_str = hda_def_path + get_relative_path(abs_path)
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
    # TODO: This seems like a fragile test and it has no explanation in the comment.
    #  Where is the number "18" coming from?
    if file_definition_str[:18] == "<hou.HDADefinition":
        file_definition_str = generate_relative_hda_definition_string(file_definition_str)
    # if file_definition_str is an OTL file path
    else:
        file_definition_str = get_relative_path(file_definition_str)

    a = hashlib.md5()
    a.update(file_definition_str)
    hash_key = a.hexdigest()
    return str(hash_key)


def get_test_data_dir():
    """
    Gets the path to ~/extract-python-from-otl/test_data

    :return: str test_data_dir: ~/extract-python-from-otl/test_data
    """
    # TODO: There are two places in your code that rely on doing "os.path.dirname(os.path.dirname())"
    #    You should do this in one place. E.g. in a function called something like "get_tool_project_path"
    #    so that the code for this function becomes simply:
    #        return os.path.join(get_tool_project_path(), "test_data")

    script_path = os.path.abspath(__file__)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
    test_data_dir = os.path.join(base_dir, "test_data")
    return test_data_dir


def get_test_otls_paths(string):
    """
    Gets a list of otl file path or path to sky_scraper.hda

    :param str string: sky_scraper.hda (or) otl_list.txt
    :return: list otl file path(s)
    """
    # TODO: As I said elsewhere, you're potentially passing in two different things, a) an OTL name or b) text file.
    #    It doesn't lead to clean code because the function prototype is not clear as to what it's expecting (regardless
    #    of what the docstring says). Either have two different arguments, or write two different functions.

    file_path = os.path.join(get_test_data_dir(), "test_otls", string)

    # if it's a text file with a list of otl file paths.
    # TODO: Use str.endswith()
    # TODO: Don't use `string` as a variable name, use something more meaningful
    if ".txt" in string:
        # access individual paths from .txt file
        with open(file_path, 'r') as file_obj:
            file_contents = file_obj.read()
            otl_file_paths = file_contents.split()
            return otl_file_paths

    # If it's just a single otl file path
    else:
        return [file_path]


def get_file_path_to_test_json_files():
    """
    Gets the path to ~/extract-python-from-otl/test_data/comparison_data

    :return: str results_dir: ~/extract-python-from-otl/test_data/comparison_data
    """

    results_dir = os.path.join(get_test_data_dir(), "comparison_data")
    return results_dir


def is_valid_datetime(input_str):
    """
    Checks if the input string represents a date and time.

    :param str input_str: date and time
    :return: bool
    """
    datetime_pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+$')
    match = datetime_pattern.match(input_str)
    # TODO: Alternatively, use match is not None (generally preferred)
    return bool(match)


def assert_json_file(file_path):
    """
    Checks whether the log.json files in the given folder tree contains all the
    appropriate keys and values.

    :param str file_path: Parent directory of otl_scripts_folder
    """

    dir_contents = os.listdir(file_path)
    for file_or_dir in dir_contents:
        # TODO: You've used `os.path.join(file_path, file_or_dir)` multiple times.
        #  You should assign it to a variable and reuse it in each situation
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
    """
    Tests and asserts the appropriate usage of shutil.rmtree()

    :param list file_paths: otl file path(s) (Tool function input)
    """
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
    'file_definition_str',
    [
        pytest.param("1"),
        pytest.param("a"),
        pytest.param(str(get_test_otls_paths("sky_scraper")[0])),
        pytest.param(str(hou.hda.definitionsInFile(get_test_otls_paths("sky_scraper.hda")[0])[0]))
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
        pytest.param(hou.hda.definitionsInFile(get_test_otls_paths("sky_scraper.hda")[0])[0],
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
        pytest.param(get_test_otls_paths("sky_scraper.hda")),
        pytest.param(get_test_otls_paths("otl_list.txt")),
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
        else:
            file_paths = get_test_otls_paths(test_data)

        epfo.extract_python(file_paths, temp_folder_path, folder_name)

    # If input is a txt file, name the .json file "multiple_otls"
    # TODO: Use str.endswith()
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
