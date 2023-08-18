# TODO: Remove commented code
# try:
#     import hou
# except ImportError:
#     # This should only happen when not running under Hython during testing
#     hou = None

import hou
import argparse
import shutil
import os
import hashlib
import json
import datetime as dt


def main():

    args = parse_args()

    if args.directory:
        otls_folder_path = args.directory

    # if text file is given, default output folder is the same is the text file,
    # else it is the current working directory
    else:
        if args.otl_paths_file:
            otls_folder_path = os.path.dirname(args.otl_paths_file)
        else:
            # the olts_folder_path is the same as the text file.
            otls_folder_path = os.getcwd()

    if args.name:
        folder_name = args.name
    else:
        folder_name = "otl_python_scripts"

    if args.otl_paths_file:
        txt_file_path = args.otl_paths_file

        # access individual paths from .txt file
        with open(txt_file_path, 'r') as file_obj:
            file_contents = file_obj.read()
            otl_file_paths = file_contents.split()

        print("\n\nGiven text file path: {0}\n\n".format(txt_file_path))

    else:
        # args.otl arg is provided instead of a list of otl pathways
        otl_file_paths = args.otl

    extract_python(otl_file_paths, otls_folder_path, folder_name)
    print("Script ran successfully\n\n")


def parse_args():
    """
    Parse args for the tool.
    :return: args
    """

    parser = argparse.ArgumentParser(description="extracts python scripts from a given list of otls")
    # text file input
    parser.add_argument("-f", "--otl_paths_file", type=str,
                        help="A file with a list of otl pathways.")
    # otl input
    parser.add_argument("-o", "--otl", type=str, nargs='*',
                        help="Pathway to an otl(s).")
    # folder name input
    parser.add_argument("-n", "--name", type=str, default="otl_scripts_folder", help="Name of the generated "
                                                                                     "scripts folder.")
    # output_folder input
    parser.add_argument("-dir", "--directory", type=str, help="An output_folder for the generated scripts folder.")

    # parse args
    args = parser.parse_args()

    if not args.otl_paths_file and not args.otl:
        parser.error("provide a text file or a specific otl path to generate the scripts folder.")

    return args


def extract_python(file_paths, otls_folder_path, name):
    """
    function to iterate through all the otls and extract all python scripts inside.

    :param list file_paths: a list of pathways to otls.
    :param str otls_folder_path: Parent directory of the scripts-folder.
    :param str name: name of the generated folder.
    """

    # create a folder to store the scripts
    scripts_folder_path = os.path.join(otls_folder_path, name)

    if not os.path.exists(scripts_folder_path):
        os.mkdir(scripts_folder_path)

    # Function to iterate through all the hdas inside each otl to
    # extract python scripts. It returns a dict containing the unique
    # names, file path and the last modified time of each otl.
    otl_hash_dict = extract_py_from_otl(file_paths, scripts_folder_path)

    print("{0} folder generated at: {1}\n\n".format(name, otls_folder_path))

    j_otl_hash_dict = json.dumps(otl_hash_dict, indent=2)
    with open(os.path.join(scripts_folder_path, "log.json"), "w") as file_obj:
        file_obj.write(j_otl_hash_dict)


def extract_py_from_otl(file_paths, scripts_folder_path):
    """
    Extracts all the python scripts inside each otl.

    :param list file_paths: list of all the otl paths.
    :param str scripts_folder_path: path to the generated scripts-folder.
    :return: dict otl_hash_dict - a dictionary of all the unique otl names [key]
            and the file paths, along with the last modified times of
            the respective otlS [value].
    """
    # TODO: Add an example above for the return data. The explanation isn't clear enough to understand
    #   exactly what's being returned here, e.g. the structure of the dict's values

    # Get all the loaded hda files in the current scene, before installing any
    default_otl_set = set(hou.hda.loadedFiles())

    # dict for storing and displaying the otl hash values
    otl_hash_dict = dict()

    # iterate through the file paths
    for file_path in file_paths:

        # check if path is valid
        if not os.path.exists(file_path):
            print("file path not valid, continuing to other hdas: {0}\n\n".format(file_path))
            continue

        try:
            hou.hda.installFile(file_path)
        except hou.Error:
            print("Could not install hda file: {0}\n\n".format(file_path))
            continue

        try:
            definitions = hou.hda.definitionsInFile(file_path)
        except hou.Error:
            print("Could not load hda file: {0}\n\n".format(file_path))
            continue


        # Make a folder for each otl
        otl_unique_name = make_unique_name(file_path, os.path.basename(file_path))
        otl_folder_path = os.path.join(scripts_folder_path, otl_unique_name)

        # checks if a scripts folder was already generated, if it was,
        # get the last modified time of the otl folders.
        if os.path.exists(otl_folder_path):
            json_file_path = os.path.join(scripts_folder_path, "log.json")
            with open(json_file_path, "r") as file_obj:
                older_time_data = json.load(file_obj)

            # if any of the otls were modified, update the scripts inside them
            # (delete the old one and generate a new one)
            if get_last_modified_time(file_path) != older_time_data[otl_unique_name][1]:
                print("{0} was modified, updating it.\n\n".format(otl_unique_name))
                shutil.rmtree(otl_folder_path)

        else:
            os.mkdir(otl_folder_path)

        # append to the otl hash dictionary
        file_dict = {"file_path" : file_path,
                     "last_mod_time" : get_last_modified_time(file_path)}
        otl_hash_dict[otl_unique_name] = file_dict

        # iterate through all the hdas inside the otl and extract the python scripts
        hda_hash_dict = extract_py_from_hda(definitions, otl_folder_path)

        # write the hda hash dict to a json file
        # TODO: Use json.dump instead to directly write out to disk.
        #   There's no need to use intermediate string variable
        j_hda_hash_dict = json.dumps(hda_hash_dict, indent=2)
        with open(os.path.join(otl_folder_path, "log.json"), "w") as file_obj:
            file_obj.write(j_hda_hash_dict)

    # Get all the hda files in the current scene after installing all the required ones.
    current_otl_set = set(hou.hda.loadedFiles())

    # Get the difference, so that only the hda files installed by the tool in
    # the current houdini session remain
    otls_installed = current_otl_set - default_otl_set

    # Uninstall all the hda files installed by the tool
    for file in otls_installed:
        hou.hda.uninstallFile(file)

    return otl_hash_dict


def extract_py_from_hda(definitions, otl_folder_path):
    """
    Extracts all python scripts inside an hda.

    :param list definitions: List of all the hda definitions inside an otl.
    :param str otl_folder_path: Parent directory of the otl-folder.
    :return: hda_hash_dict - a dictionary of all the unique hda names [key]
            and their name and context [value].
    """
    # TODO: Add an example above for the return data. The explanation isn't clear enough to understand
    #   exactly what's being returned here, e.g. the structure of the dict's values

    # dict for storing and displaying the hda hash values
    hda_hash_dict = dict()

    # Make a folder for each hda and extract the python files inside
    for definition in definitions:
        hda_unique_name = make_unique_name(str(definition), str(definition.nodeTypeName()))
        hda_folder_path = os.path.join(otl_folder_path, hda_unique_name)

        if not os.path.exists(hda_folder_path):
            os.mkdir(hda_folder_path)

        # extract the python scripts inside all the components of the hda and write to file
        extract_py_and_write(definition, hda_folder_path)

        # append to the hda hash dictionary
        try:
            hda_node_type_and_context = definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()
        except hou.Error:
            # TODO: This is not correct, you should be doing this:
            #   except hou.Error as exc:
            #       hda_node_type_and_context = str(exc)

            # TODO: This isn't a particularly nice thing to do, as you're mixing error reports with your data
            #   Why not pass a list, dict, or other object into the function that you can store error messages in?
            hda_node_type_and_context = str(hou.Error)

        hda_hash_dict[
            hda_unique_name] = hda_node_type_and_context

    return hda_hash_dict


def make_unique_name(file_definition_string, name):
    """
    Makes a unique name with a hash for an hda or an otl.

    :param str name: otl or hda name
    :param str file_definition_string: A file path of an otl or an hda.
    :return: A hashed name of an otl or an hda.
    """
    # TODO: Again, it's helpful to give an example of what you're returning for a given input

    hash_key = get_hash(file_definition_string)
    unique_name = name + "_" + hash_key
    unique_name = unique_name.replace("/", "_").replace(" ", "_").replace(".", "_")
    return unique_name


def get_hash(file_definition_str):
    """
    Generates a unique hash for the input.

    input for otl folder name hash = file path of otl
    input for hda folder name hash = str(definition of hda)

    :param str file_definition_str: A str(hda definition) of an otl file path
    :return: a hash key
    """

    a = hashlib.md5()
    a.update(file_definition_str)
    hash_key = a.hexdigest()
    return str(hash_key)


def get_last_modified_time(file_path):
    """
    Gets the last modified time of an otl file.

    :param str file_path: File path to an otl.
    :return: String of the last modified time of the hda.
    """
    # TODO: The function name is likely to lead people to believe that you're returning a date object instance,
    #    not a string. I'd suggest either renaming the function to `get_last_modified_time_str()` or leaving it
    #    as it is, and don't convert it to a string when you return it. Instead, convert it to a string where
    #    it's being called.

    modify_time = os.path.getmtime(file_path)
    modify_date = dt.datetime.fromtimestamp(modify_time)
    return str(modify_date)


def extract_py_and_write(definition, hda_folder_path):
    """
    Extracts all the python scripts inside an hda and writes it to a file on disk.

    :param <hou.HDADefinition> definition: hda file definition.
    :param str hda_folder_path: Directory of the generated hda folder.
    """

    # Extract python scripts in the scripts tab.
    # TODO: remove the "_1" suffix. In fact, you don't even need this variable. You can just move this call inside
    #     the "write_result_to_disk" function.
    result_1 = extract_py_scripts(definition, hda_folder_path)
    write_result_to_disk(result_1)

    try:
        ptg = definition.parmTemplateGroup()
        parm_templates = ptg.parmTemplates()
    except hou.Error:
        print("\n\nCould not access parm templates of: {0}\n\n".format(str(definition)))
        return

    # exclude hdas with no parameters
    # TODO: Just do "if parm_templates:". It'll evaluate to True if it's not None and not empty.
    if len(parm_templates) != 0:

        # iterate through each parameter
        for parm_template in parm_templates:

            # Extract python scripts in the item generation tab inside certain parameters.
            # TODO: Same here with the "_2"
            result_2 = extract_item_generation_scripts(hda_folder_path, parm_template)
            write_result_to_disk(result_2)

            # Extract python scripts in the parameter callbacks.
            # TODO: Same here with the "_3"
            result_3 = extract_parameter_callbacks(hda_folder_path, parm_template)
            write_result_to_disk(result_3)


def write_result_to_disk(result):
    # TODO: You might want to flatten the nesting by inverting the logic and using return/continue

    # Checks if the input dictionary has valid data
    # TODO: Unless I'm misunderstanding something here, you should just do "if result:" instead
    if result is not dict():
        for filename, data in result.items():
            # check if file exists, if it does, don't update it
            if not os.path.exists(filename):
                with open(filename, 'w') as file_obj:
                    file_obj.write(data)


def extract_parameter_callbacks(hda_folder_path, parm_template):
    """
    Extracts the python scripts inside the parameter callbacks (if any).

    :param str hda_folder_path: Directory of the generated hda folder.
    :param <hou.ParmTemplate> parm_template: hda parameter template.
    :return dict result: dict containing all the callback python scripts.
    """
    # TODO: Add an explanation of what the key/values are in the dict being returned, plus an example.

    result = {}

    parameter_callback_folder = os.path.join(hda_folder_path, "parameter_callbacks")

    # check if a callback script exists, and if it's in python
    if parm_template.scriptCallbackLanguage() == hou.scriptLanguage.Python and len(parm_template.scriptCallback()) > 0:

        # parameter callback folder
        if not os.path.exists(parameter_callback_folder):
            os.mkdir(parameter_callback_folder)

        callback_py_script = parm_template.scriptCallback()
        script_name = parm_template.name()
        script_file_path = os.path.join(parameter_callback_folder, script_name + ".py")

        # TODO: what happens if `script_file_path` is already in result? Is that even possible? If it can potentially
        #   happen, it shouldn't just overwrite it, right? (Feels like a good candidate to test in a unit test)
        result[script_file_path] = callback_py_script

    return result


def extract_item_generation_scripts(hda_folder_path, parm_template):
    """
    Extracts the item generation scripts inside certain the parameters (if any).

    :param hda_folder_path: Directory of the generated hda folder.
    :param <hou.ParmTemplate> parm_template: hda parameter template.
    :return dict result: dict containing all the item generation python scripts.
    """
    # TODO: Add an explanation of what the key/values are in the dict being returned, plus an example.

    result = {}

    # name item generation scripts folder
    item_generation_scripts_folder = os.path.join(hda_folder_path, "item_generation_scripts")

    # check if an item generation script exists, and if it's in python
    if isinstance(parm_template, hou.StringParmTemplate) \
            or isinstance(parm_template, hou.MenuParmTemplate) \
            or isinstance(parm_template, hou.IntParmTemplate):
        if parm_template.itemGeneratorScriptLanguage() == hou.scriptLanguage.Python:
            if len(parm_template.itemGeneratorScript()) > 0:
                item_generation_script = parm_template.itemGeneratorScript()
                file_name = parm_template.name()

                # create item generation scripts folder
                if not os.path.exists(item_generation_scripts_folder):
                    os.mkdir(item_generation_scripts_folder)

                script_file_path = os.path.join(item_generation_scripts_folder, file_name + ".py")

                # TODO: what happens if `script_file_path` is already in result? Is that even possible? If it can potentially
                #   happen, it shouldn't just overwrite it, right? (Feels like a good candidate to test in a unit test)
                result[script_file_path] = item_generation_script

    return result


def extract_py_scripts(definition, hda_folder_path):
    """
    Extracts the python scripts inside the scripts tab of the hda file (if any).

    :param <hou.HDADefinition> definition: hda file definition.
    :param str hda_folder_path: Directory of the generated hda folder.
    :return dict result: dict containing all the main python scripts.
    """
    # TODO: Add an explanation of what the key/values are in the dict being returned, plus an example.

    result = {}

    # folder name for the main python scripts
    main_py_scripts_folder = os.path.join(hda_folder_path, "main_python_scripts")

    try:
        # pull out the python scripts in the scripts tab
        definition_sections = definition.sections()
        efo = definition.extraFileOptions()
    except hou.Error:
        print("\n\nCould not access hda definition sections: {0}\n\n".format(str(definition)))
        # TODO: See my comment about exceptions on line 230 on how to get the exception instance
        # error_dict = {"hou Error" : hou.Error.exceptionTypeName(),
        #               "Error message" : hou.Error.instanceMessage()}
        # print(json.dumps(error_dict, indent=4))
        # TODO: You can just return "result" here. It's already set to an empty dictionary
        return dict()

    # iterate through each section
    for section in definition_sections:

        # check if it's a python script
        if section + "/IsPython" in efo.keys() and efo[section + "/IsPython"]:
            py_script = definition_sections[section].contents()
            file_name = definition_sections[section].name()

            # check and rectify the file name for any potential bad names
            # TODO: If you have time, you might find it helpful to learn about
            #     doing a replace operation using regular expressions.
            file_name = file_name.replace('/', '_').replace('.', '_').replace(' ', '_')

            # making a folder for the main python scripts
            if not os.path.exists(main_py_scripts_folder):
                os.mkdir(main_py_scripts_folder)

            script_file_path = os.path.join(main_py_scripts_folder, file_name + ".py")
            # TODO: what happens if `script_file_path` is already in result? Is that even possible? If it can potentially
            #   happen, it shouldn't just overwrite it, right? (Feels like a good candidate to test in a unit test)
            result[script_file_path] = py_script

    return result


if __name__ == '__main__':
    main()
