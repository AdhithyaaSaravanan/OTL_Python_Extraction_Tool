import os
import re
import pytest
from contextlib import contextmanager
import mock
import commslib.temp as cm
import shutil
import hashlib
import datetime as dt

try:
    import hou
except ImportError:
    # This should only happen when not running under Hython during testing
    hou = None

import extract_python_from_otl as epfo


@pytest.mark.parametrize(
    ('file_paths',
     'path_exists_return_value',
     'extract_py_from_hda_call_count',
     'path_exists_call_count',
     'make_dir_call_count',
     'del_folder_call_count'),
    [
        pytest.param(["/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda"],
                     True, 1, 2, 0, 1),
        pytest.param(["/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda"],
                     False, 0, 1, 0, 0),
        pytest.param([], False, 0, 0, 0, 0)
    ]
)
def test_extract_py_from_otl(file_paths,
                             path_exists_return_value,
                             extract_py_from_hda_call_count,
                             path_exists_call_count,
                             make_dir_call_count,
                             del_folder_call_count):
    with mock.patch("__builtin__.open", mock.mock_open(read_data="mocked_data")) as opn, \
         mock.patch("extract_python_from_otl.extract_py_from_hda") as extract_py_from_hda, \
         mock.patch("os.path.exists") as path_exists, \
         mock.patch("os.mkdir") as make_dir, \
         mock.patch("json.load") as json_load, \
         mock.patch("json.dumps") as json_dumps, \
         mock.patch("shutil.rmtree") as del_folder:

        path_exists.return_value = path_exists_return_value

        # generate expected result dict
        expected_result = dict()

        if path_exists_return_value:
            a = hashlib.md5()
            for file_path in file_paths:

                a.update(str(file_path))
                hash_key = a.hexdigest()
                otl_name = os.path.basename(file_path)
                unique_name = otl_name + "_" + str(hash_key)
                unique_name = unique_name.replace("/", "_").replace(" ", "_").replace(".", "_")

                otl_last_mod_time = str(dt.datetime.fromtimestamp(os.path.getmtime(file_path)))
                file_dict = {"file_path" : file_path,
                             "last_mod_time" : otl_last_mod_time}
                expected_result.update({unique_name : file_dict})

        scripts_folder_path = "/tmp"
        result = epfo.extract_py_from_otl(file_paths, scripts_folder_path)

    assert result == expected_result
    assert extract_py_from_hda.call_count == extract_py_from_hda_call_count
    assert path_exists.call_count == path_exists_call_count
    assert make_dir.call_count == make_dir_call_count
    assert del_folder.call_count == del_folder_call_count


@pytest.mark.parametrize(
    ('otl_file_path',
     'make_dir_call_count',
     'path_exists_return_value',
     'path_exists_call_count',
     'extract_py_and_write_call_count'),

    [
        pytest.param("/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda",
                     1, False, 1, 1),
        pytest.param("/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda",
                     0, True, 1, 1),
        pytest.param(None, 0, True, 0, 0)
    ]
)
def test_extract_py_from_hda(otl_file_path,
                             make_dir_call_count,
                             path_exists_return_value,
                             path_exists_call_count,
                             extract_py_and_write_call_count):

    with mock.patch("extract_python_from_otl.extract_py_and_write") as extract_py_and_write,\
         mock.patch("os.path.exists") as path_exists,\
         mock.patch("os.mkdir") as make_dir:

        path_exists.return_value = path_exists_return_value

        try:
            definitions = hou.hda.definitionsInFile(otl_file_path)
            hou.hda.installFile(otl_file_path)
        except:
            definitions = []

        otl_folder_path = "/tmp"

        # generate unique names for all hda definitions and store inside a list
        expected_result_dict = dict()
        a = hashlib.md5()
        for definition in definitions:
            a.update(str(definition))
            hash_key = a.hexdigest()
            name = definition.nodeTypeName()
            unique_name = str(name) + "_" + str(hash_key)
            unique_name = unique_name.replace("/", "_").replace(" ", "_").replace(".", "_")
            expected_result_dict.update({unique_name : definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()})

        result = epfo.extract_py_from_hda(definitions, otl_folder_path)

    assert result == expected_result_dict
    assert make_dir.call_count == make_dir_call_count
    assert path_exists.call_count == path_exists_call_count
    assert extract_py_and_write.call_count == extract_py_and_write_call_count


@pytest.mark.parametrize(
    'var',
    [
        pytest.param(1),
        pytest.param("a"),
        pytest.param("/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda"),
        pytest.param(hou.hda.definitionsInFile
                    ("/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda")[0])
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
def test_extract_py_and_write(scripts_folder_name, file_name ,expected_script):

    file_path = "/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda"
    definition = hou.hda.definitionsInFile(file_path)[0]
    temp_folder_name = "otl_python_extraction_tool_test"
    hda_folder_path = cm.make_directory(temp_folder_name)

    hou.hda.installFile(file_path)

    epfo.extract_py_and_write(definition, hda_folder_path)

    script_file_path = hda_folder_path + scripts_folder_name + file_name
    with open(script_file_path, 'r') as file_obj:
        content = file_obj.read()
        assert content == expected_script

    del_dir = os.path.dirname(os.path.dirname(hda_folder_path))
    if os.path.basename(del_dir) == temp_folder_name:
        shutil.rmtree(del_dir)


@pytest.mark.parametrize(
    ('path_exists_return_value', 'func_arg', 'path_exists_call_count', 'opn_call_count'),
    [
        pytest.param(False, {"file_path" : "python_script"}, 1, 1),
        pytest.param(True, {"file_path" : "python_script"}, 1, 0),
        pytest.param(False, {}, 0, 0),
        pytest.param(True, {}, 0, 0),
    ]
)
def test_write_result_to_disk(path_exists_return_value, func_arg, path_exists_call_count, opn_call_count):
    with mock.patch("__builtin__.open", mock.mock_open(read_data="mocked_data")) as opn, \
         mock.patch("os.path.exists") as path_exists:

        path_exists.return_value = path_exists_return_value
        epfo.write_result_to_disk(func_arg)

    assert path_exists.call_count == path_exists_call_count
    assert opn.call_count == opn_call_count

    # didn't mock file_obj.write()


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
    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir") as make_dir:
        path_exists.return_value = True

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
                    {"/tmp/item_generation_scripts/test_int.py" : "print 'hello'"}),
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
    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir") as make_dir:
        path_exists.return_value = True

        hda_folder_path = "/tmp"
        result = epfo.extract_item_generation_scripts(hda_folder_path, parm_template)
        assert result == expected


@pytest.mark.parametrize(
    ('definition', 'file_names', 'expected_scripts'),
    [
        pytest.param(hou.hda.definitionsInFile
                    ("/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda")[0],
                    ['/OnCreated.py', '/OnUpdated.py', '/PythonModule.py'],
                    ['print("onCreated")', 'print("onUpdated")', 'print("Python script")'])
    ]
)
def test_extract_py_scripts(definition, file_names, expected_scripts):

    with mock.patch("os.path.exists") as path_exists, mock.patch("os.mkdir") as make_dir:
        path_exists.return_value = True

        hda_folder_path = "/tmp"
        general_file_path = hda_folder_path + "/main_python_scripts"

        # prepare the keys / file paths of the result dict
        file_paths = []
        for file_name in file_names:
            file_paths.append(general_file_path + file_name)

        # initial and make expected result dict
        expected_result_dict = dict()
        for file_path in file_paths:
            expected_result_dict.update({file_path : expected_scripts[file_paths.index(file_path)]})

        result = epfo.extract_py_scripts(definition, hda_folder_path)
        assert result == expected_result_dict



# @pytest.mark.parametrize(
#     'file_paths',
#     [
#         pytest.param(["/job/commsdev/td/dev/asaravan/git/tools/extract-python-from-otl/test_data_and_results/sky_scraper.hda"])
#     ]
# )
# def test_extract_python(file_paths):
#
#     temp_folder_name = otl_python_extraction_tool_test
#     otls_folder_path = cm.make_directory(temp_folder_name)
#     scripts_folder_name = "otl_scripts"
#     epfo.extract_python(file_paths, otls_folder_path, scripts_folder_name)
#

