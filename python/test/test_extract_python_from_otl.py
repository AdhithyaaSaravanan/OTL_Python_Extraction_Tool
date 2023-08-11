import json
import os
import re
import pytest
import mock
import commslib.temp as cm
import shutil
import hou

# try:
#     import hou
# except ImportError:
#     # This should only happen when not running under Hython during testing
#     hou = None

import extract_python_from_otl as epfo


# If the test OTLs have been modified, the test data has to be generated again.


def generate_folder_tree_dict(folder_path):

    result = {}
    if os.path.isdir(folder_path):
        items = os.listdir(folder_path)
        for item in items:
            item_path = os.path.join(folder_path, item)
            result[item] = generate_folder_tree_dict(item_path)
    elif os.path.isfile(folder_path):
        with open(folder_path, 'r') as file:
            result = {'file_contents': file.read()}
    return result


# gets path to ./extract-python-from-otl/test_data_and_results
def get_test_data_dir():

    script_path = os.path.abspath(__file__)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
    test_data_dir = os.path.join(base_dir, "test_data_and_results")
    return test_data_dir


# gets path to ./extract-python-from-otl/test_data_and_results/test_otls/"string variable"
def get_test_otls_path(string):

    abs_path_to_test_otl = os.path.join(get_test_data_dir(), "test_otls", string)
    return abs_path_to_test_otl


# gets path to ./extract-python-from-otl/test_data_and_results/pytest_results_to_compare
def get_file_path_to_test_json_files():

    results_dir = os.path.join(get_test_data_dir(), "pytest_results_to_compare")
    return results_dir


@pytest.mark.parametrize(
    'file_paths',
    [
        pytest.param([get_test_otls_path("sky_scraper.hda")]),
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
        pytest.param(1),
        pytest.param("a"),
        pytest.param(get_test_otls_path("sky_scraper")),
        pytest.param(hou.hda.definitionsInFile(get_test_otls_path("sky_scraper.hda"))[0])
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
    file_path = get_test_otls_path("sky_scraper.hda")
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
        pytest.param(hou.hda.definitionsInFile(get_test_otls_path("sky_scraper.hda"))[0],
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


def test_extract_python_full_functionality():

    temp_folder_name = "otl_python_extraction_tool_test"
    temp_folder_path = cm.make_directory(temp_folder_name)

    assert temp_folder_name in temp_folder_path

    folder_name = "otl_python_scripts"
    file_paths = [get_test_otls_path("sky_scraper.hda")]

    epfo.extract_python(file_paths, temp_folder_path, folder_name)

    definition = hou.hda.definitionsInFile(file_paths[0])[0]
    hou.hda.installFile(file_paths[0])

    otl_unique_name = epfo.make_unique_name(file_paths[0])
    hda_unique_name = epfo.make_unique_name(definition)

    expected_roots_ = [temp_folder_path, os.path.join(temp_folder_path, folder_name),
                       os.path.join(temp_folder_path, folder_name, otl_unique_name),
                       os.path.join(temp_folder_path, folder_name, otl_unique_name, hda_unique_name),
                       os.path.join(temp_folder_path, folder_name, otl_unique_name, hda_unique_name,
                                    "parameter_callbacks"),
                       os.path.join(temp_folder_path, folder_name, otl_unique_name, hda_unique_name,
                                    "main_python_scripts"),
                       os.path.join(temp_folder_path, folder_name, otl_unique_name, hda_unique_name,
                                    "item_generation_scripts")]

    expected_dirs_ = [[folder_name],
                      [otl_unique_name],
                      [hda_unique_name],
                      ['parameter_callbacks', 'main_python_scripts', 'item_generation_scripts'],
                      [], [], []]

    expected_files_ = [[], ["log.json"], ["log.json"], [], ['button.py'],
                       ['OnCreated.py', 'PythonModule.py', 'OnUpdated.py'],
                       ['button.py']]

    i = 0
    expected = True
    for roots, dirs, files in os.walk(temp_folder_path):
        if not roots == expected_roots_[i] or not dirs == expected_dirs_[i] or not files == expected_files_[i]:
            expected = False
        i = i + 1

    assert expected

    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)


def test_functionality():

    test_otl_data_name = "sky_scraper_otl"
    temp_folder_name = "otl_python_extraction_tool_test"
    temp_folder_path = cm.make_directory(temp_folder_name)

    assert temp_folder_name in temp_folder_path

    folder_name = "otl_scripts_folder"
    file_paths = [get_test_otls_path("sky_scraper.hda")]

    epfo.extract_python(file_paths, temp_folder_path, folder_name)

    # get expected data
    test_json_file_path = os.path.join(get_file_path_to_test_json_files(), test_otl_data_name + ".json")
    with open(test_json_file_path, "r") as file_obj:
        expected_data = json.load(file_obj)

    # get current tool generated data
    folder_tree_dict = generate_folder_tree_dict(temp_folder_path)

    # compare both the data
    # print(json.dumps(folder_tree_dict, indent=4))
    assert folder_tree_dict == expected_data

    # clean up
    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)
