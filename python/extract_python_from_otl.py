try:
    import hou
except ImportError:
    # This should only happen when not running under Hython during testing
    hou = None

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

    # dict for storing and displaying the otl hash values
    otl_hash_dict = dict()

    # iterate through the file paths
    for file_path in file_paths:

        # check if path is valid
        if not os.path.exists(file_path):
            # print("file path not valid, continuing to other hdas: {0}\n\n".format(file_path))
            continue

        try:
            definitions = hou.hda.definitionsInFile(file_path)
        except hou.Error:
            print("Could not load hda file: {0}\n\n".format(file_path))
            continue

        try:
            hou.hda.installFile(file_path)
        except hou.Error:
            print("Could not install hda file: {0}\n\n".format(file_path))
            continue

        # Make a folder for each otl
        otl_unique_name = make_unique_name(file_path)
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
        j_hda_hash_dict = json.dumps(hda_hash_dict, indent=2)
        with open(os.path.join(otl_folder_path, "log.json"), "w") as file_obj:
            file_obj.write(j_hda_hash_dict)

    return otl_hash_dict


def extract_py_from_hda(definitions, otl_folder_path):
    """
    Extracts all python scripts inside an hda.

    :param list definitions: List of all the hda definitions inside an otl.
    :param str otl_folder_path: Parent directory of the otl-folder.
    :return: hda_hash_dict - a dictionary of all the unique hda names [key]
            and the file paths [value].
    """

    # dict for storing and displaying the hda hash values
    hda_hash_dict = dict()

    # Make a folder for each hda and extract the python files inside
    for definition in definitions:
        hda_unique_name = make_unique_name(definition)
        hda_folder_path = os.path.join(otl_folder_path, hda_unique_name)

        if not os.path.exists(hda_folder_path):
            os.mkdir(hda_folder_path)

        # extract the python scripts inside all the components of the hda and write to file
        extract_py_and_write(definition, hda_folder_path)

        # append to the hda hash dictionary
        hda_hash_dict[
            hda_unique_name] = definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()

    return hda_hash_dict


def make_unique_name(var):
    """
    Makes a unique name with a hash for an hda or an otl.
    
    Input for otl folder name hash = String of file path of otl.
    Input for hda folder name hash = Definition of an hda.

    :param var: Either a str (file path of an otl) or an hda definition.
    :return: A hashed name of an otl or an hda.
    """

    hash_key = get_hash(var)

    # if var is an hda definition
    if isinstance(var, hou.HDADefinition):
        name = var.nodeTypeName()
        unique_name = str(name) + "_" + str(hash_key)

    # if var is a str(file path for an otl)
    else:
        otl_name = os.path.basename(var)
        unique_name = otl_name + "_" + str(hash_key)

    unique_name = unique_name.replace("/", "_").replace(" ", "_").replace(".", "_")
    return unique_name


def get_hash(var):
    """
    Generates a unique hash for the input.

    input for otl folder name hash = string of file path of otl
    input for hda folder name hash = definition of hda

    :param var: either a str(file path of an otl) or a hda definition
    :return: a hash key
    """

    a = hashlib.md5()
    a.update(str(var))
    hash_key = a.hexdigest()
    return hash_key


def get_last_modified_time(file_path):
    """
    Gets the last modified time of an otl file.

    :param str file_path: File path to an otl.
    :return: String of the last modified time of the hda.
    """

    modify_time = os.path.getmtime(file_path)
    modify_date = dt.datetime.fromtimestamp(modify_time)
    return str(modify_date)


def extract_py_and_write(definition, hda_folder_path):
    """
    Extracts all the python scripts inside an hda and writes it to a file on disk.

    (input for otl folder name hash = string of file path of otl
    input for hda folder name hash = definition of hda)

    :param definition: hda file definition.
    :param hda_folder_path: Directory of the generated hda folder.
    """

    # Extract python scripts in the scripts tab.
    result_1 = extract_py_scripts(definition, hda_folder_path)
    write_result_to_disk(result_1)

    ptg = definition.parmTemplateGroup()
    pt = ptg.parmTemplates()

    # exclude hdas with no parameters
    if len(pt) != 0:

        # iterate through each parameter
        for parm_template in pt:

            # Extract python scripts in the item generation tab inside certain parameters.
            result_2 = extract_item_generation_scripts(hda_folder_path, parm_template)
            write_result_to_disk(result_2)

            # Extract python scripts in the parameter callbacks.
            result_3 = extract_parameter_callbacks(hda_folder_path, parm_template)
            write_result_to_disk(result_3)


def write_result_to_disk(result):

    for filename, data in result.items():
        # check if file exists, if it does, don't update it
        if not os.path.exists(filename):
            with open(filename, 'w') as file_obj:
                file_obj.write(data)


def extract_parameter_callbacks(hda_folder_path, parm_template):
    """
    Extracts the python scripts inside the parameter callbacks (if any).

    :param str hda_folder_path: Directory of the hda file.
    :param parm_template: hda parameter template.
    :return dict result: dict of all the python scripts
    """

    result = {}

    # check if a callback script exists, and if it's in python
    if parm_template.scriptCallbackLanguage() == hou.scriptLanguage.Python and len(parm_template.scriptCallback()) > 0:

        # parameter callback folder
        parameter_callback_folder = os.path.join(hda_folder_path, "parameter_callbacks")
        if not os.path.exists(parameter_callback_folder):
            os.mkdir(parameter_callback_folder)

        callback_py_script = parm_template.scriptCallback()
        script_name = parm_template.name()
        script_file_path = os.path.join(parameter_callback_folder, script_name + ".py")

        result[script_file_path] = callback_py_script

    return result


def extract_item_generation_scripts(hda_folder_path, parm):
    """
    Extracts the item generation scripts inside certain the parameters (if any).

    :param hda_folder_path: Directory of the generated hda folder.
    :param parm: hda parameter.
    """

    result = {}

    # check if an item generation script exists, and if it's in python
    if isinstance(parm, hou.StringParmTemplate) \
            or isinstance(parm, hou.MenuParmTemplate) \
            or isinstance(parm, hou.IntParmTemplate):
        if parm.itemGeneratorScriptLanguage() == hou.scriptLanguage.Python:
            if len(parm.itemGeneratorScript()) > 0:
                item_generation_script = parm.itemGeneratorScript()
                file_name = parm.name()

                # item generation scripts folder
                item_generation_scripts_folder = os.path.join(hda_folder_path, "item_generation_scripts")
                if not os.path.exists(item_generation_scripts_folder):
                    os.mkdir(item_generation_scripts_folder)

                script_file_path = os.path.join(item_generation_scripts_folder, file_name + ".py")

                result[script_file_path] = item_generation_script

    return result


def extract_py_scripts(definition, hda_folder_path):
    """
    Extracts the python scripts inside the scripts tab of the hda file (if any).

    :param definition: hda file definition.
    :param hda_folder_path: Directory of the generated hda folder.
    """

    result = {}

    # making a folder for the main python scripts
    main_py_scripts_folder = os.path.join(hda_folder_path, "main_python_scripts")
    if not os.path.exists(main_py_scripts_folder):
        os.mkdir(main_py_scripts_folder)

    # pull out the python scripts in the scripts tab
    definition_sections = definition.sections()
    efo = definition.extraFileOptions()

    # iterate through each section
    for section in definition_sections:

        # check if it's a python script
        if section + "/IsPython" in efo.keys() and efo[section + "/IsPython"]:
            py_script = definition_sections[section].contents()
            file_name = definition_sections[section].name()

            # check and rectify the file name for any potential bad names
            file_name = file_name.replace('/', '_').replace('.', '_').replace(' ', '_')

            script_file_path = os.path.join(main_py_scripts_folder, file_name + ".py")

            result[script_file_path] = py_script

    return result



if __name__ == '__main__':
    main()
