#!/usr/bin/env hython

# CM_NO_SGTK=1

# import sys
import hou
import argparse
import shutil
import os
import hashlib
import json
import datetime as dt


def main():

    args = parse_args()

    if args.output_folder:
        otls_folder_path = args.output_folder

    # if text file is given, default folder output_folder is the same is the text file,
    # else it is the same as the tool.
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
            otl_file_paths = file_obj.readlines()

        print("\n\nGiven text file path: {0}\n\n".format(txt_file_path))

    else:
        # args.otl arg is provided instead of a list of otl pathways
        otl_file_paths = args.otl

    extract(otl_file_paths, otls_folder_path, folder_name)
    print("Script ran successfully\n\n")


def parse_args():
    """
    Parse args for the tool.
    :return: args
    """

    parser = argparse.ArgumentParser(description="extracts python scripts from a given list of otls")
    # text file input
    parser.add_argument("-f", "--otl_paths_file", type=str,
                        help="A text file with a list of otl pathways.")
    # otl input
    parser.add_argument("-o", "--otl", type=str, nargs='*',
                        help="Pathway to an otl.")
    # folder name input
    parser.add_argument("-n", "--name", type=str, default="otl_scripts_folder", help="A name for the generated "
                                                                                     "scripts folder.")
    # output_folder input
    parser.add_argument("-dir", "--output_folder", type=str, help="A output_folder for the generated scripts folder.")

    # parse args
    args = parser.parse_args()

    if not args.otl_paths_file and not args.otl:
        parser.error("provide a text file or a specific otl path to generate the scripts folder.")

    return args


def extract(file_paths, otls_folder_path, name):
    """
    function to iterate through all the otls and extract all python scripts inside.

    :param str otls_folder_path: a text file containing a list of pathways to otls
    :param list file_paths: a list of pathways to otls
    :param str name: name of the generated folder
    """

    # create a folder to store the scripts
    scripts_folder_exists = False
    scripts_folder_path = os.path.join(otls_folder_path, name)
    # if a different name is given, then it doesn't detect it.

    # check if the script had already been run once, i.e. the scripts folder already exists.
    if os.path.exists(scripts_folder_path):
        scripts_folder_exists = True
    else:
        os.mkdir(scripts_folder_path)

    otl_hash_dict = extract_py_from_otl(file_paths, name, otls_folder_path, scripts_folder_exists, scripts_folder_path)

    # write the otl hash dict to a json file
    j_otl_hash_dict = json.dumps(otl_hash_dict, indent=2)
    with open(os.path.join(scripts_folder_path, "log.json"), "w") as file_obj:
        file_obj.write(j_otl_hash_dict)


def extract_py_from_otl(file_paths, name, otls_folder_path, scripts_folder_exists, scripts_folder_path):
    """
    Extracts all python scripts inside an OTL.

    :param list file_paths: list of all the otl paths.
    :param str name: name of the scripts-folder.
    :param str otls_folder_path: directory of the scripts-folder.
    :param bool scripts_folder_exists: True if the scripts folder already exists,
            i.e. the tool has already been run before.
    :param scripts_folder_path:
    :return: otl_hash_dict - a dictionary of all the unique otl names [key]
            and the directory of the files they correspond to, along with
            the last modified times of the respective OTLS [value].
    """

    # dict for storing and displaying the otl hash values
    otl_hash_dict = dict()

    # iterate through the file paths
    for file_path in file_paths:

        # check if path is valid
        if not os.path.exists(file_path):
            print("file path not valid, continuing to other HDAs: {0}\n\n".format(file_path))
            continue

        try:
            definitions = hou.hda.definitionsInFile(file_path)
        except hou.Error:
            print("Could not load HDA file: {0}\n\n".format(file_path))
            continue

        try:
            hou.hda.installFile(file_path)
        except hou.Error:
            print("Could not install HDA file: {0}\n\n".format(file_path))
            continue

        # Make a folder for each OTL
        otl_unique_name = make_unique_name(file_path)
        otl_folder_path = os.path.join(scripts_folder_path, otl_unique_name)

        # checks if a scripts folder was already generated, if it was,
        # get the last modified time of the otl folders.
        if scripts_folder_exists:
            # print("scripts folder already exists\n\n")
            json_file_path = os.path.join(scripts_folder_path, "log.json")
            with open(json_file_path, "r") as file_obj:
                older_time_data = json.load(file_obj)

            # if any of the otls were modified, update the scripts inside them
            # (delete the old one and generate a new one)
            if get_last_modified_time(file_path) != older_time_data[otl_unique_name][1]:
                print("{0} was modified, updating it.\n\n".format(otl_unique_name))
                shutil.rmtree(otl_folder_path)
            else:
                # print("None of the OTLs were modified, proceeding as normal.\n\n")
                pass

        if not os.path.exists(otl_folder_path):
            os.mkdir(otl_folder_path)

        # append to the otl hash dictionary
        otl_hash_dict[otl_unique_name] = file_path, "last_mod_time: " + get_last_modified_time(file_path)

        # iterate through all the HDAs inside the OTl and extract the python scripts
        hda_hash_dict = extract_py_from_hda(definitions, otl_folder_path)

        # write the hda hash dict to a json file
        j_hda_hash_dict = json.dumps(hda_hash_dict, indent=2)
        with open(os.path.join(otl_folder_path, "log.json"), "w") as file_obj:
            file_obj.write(j_hda_hash_dict)

    print("{0} folder generated at: {1}\n\n".format(name, otls_folder_path))
    return otl_hash_dict


def extract_py_from_hda(definitions, otl_folder_path):
    """
    Extracts all python scripts inside an HDA.

    :param definitions: All the HDA definitions inside an OTL.
    :param str otl_folder_path: Directory of the OTL-folder.
    :return: hda_hash_dict - a dictionary of all the unique hda names [key]
            and the directory of the files they correspond to [value].
    """

    # dict for storing and displaying the hda hash values
    hda_hash_dict = dict()

    # Make a folder for each HDA and extract the python files inside
    for definition in definitions:
        hda_unique_name = make_unique_name(definition)
        hda_folder_path = os.path.join(otl_folder_path, hda_unique_name)

        if not os.path.exists(hda_folder_path):
            pass

        # extract the python scripts inside all the components of the HDA and write to file
        extract_py_and_write(definition, hda_folder_path)

        # append to the hda hash dictionary
        hda_hash_dict[
            hda_unique_name] = definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()

    return hda_hash_dict


def make_unique_name(var):
    """
    Makes a unique for an HDA or an OTL.
    
    Input for otl folder name hash = string of file path of otl.
    Input for hda folder name hash = definition of hda.

    :param var: Either a str (file path of an otl) or a hda definition.
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
    Gets the last modified time of an HDA file.

    :param str file_path: file path to an hda
    :return: string of the last modified time of the hda
    """

    modify_time = os.path.getmtime(file_path)
    modify_date = dt.datetime.fromtimestamp(modify_time)
    return str(modify_date)


def extract_py_and_write(definition, hda_folder_path):
    """
    Extracts all the python scripts inside an HDA and writes it to a file on disk.

    (input for otl folder name hash = string of file path of otl
    input for hda folder name hash = definition of hda)

    :param definition: hda file definition
    :param hda_folder_path: string containing the folder name
    """

    extract_py_scripts(definition, hda_folder_path)

    # pull out the call back scripts from separate parameters
    # access each parameter
    ptg = definition.parmTemplateGroup()
    pt = ptg.parmTemplates()

    # exclude hdas with no parameters
    if len(pt) != 0:

        # iterate through each parameter
        for parm in pt:

            extract_menu_scripts(hda_folder_path, parm)
            extract_parameter_callbacks(hda_folder_path, parm)


def extract_parameter_callbacks(hda_folder_path, parm):
    """
    Extracts the python scripts inside the parameter callbacks (if any).

    :param str hda_folder_path: Scripts directory of the HDA file.
    :param parm: HDA parameter.
    """

    # check if a callback script exists, and if it's in python
    if parm.scriptCallbackLanguage() == hou.scriptLanguage.Python and len(parm.scriptCallback()) > 0:

        # parameter callback folder
        parameter_callback_folder = os.path.join(hda_folder_path, "parameter_callbacks")
        if not os.path.exists(parameter_callback_folder):
            os.mkdir(parameter_callback_folder)

        callback_py_script = parm.scriptCallback()
        script_name = parm.name()
        script_file_path = os.path.join(parameter_callback_folder, script_name + ".py")

        # check if file exists, if it does, don't update it
        if not os.path.exists(script_file_path):
            with open(script_file_path, 'w') as file_obj:
                file_obj.write(callback_py_script)


def extract_menu_scripts(hda_folder_path, parm):
    """
    Extracts the python scripts inside the all the parameters that have a menu (if any).

    :param hda_folder_path: Scripts directory of the HDA file.
    :param parm: HDA parameter.
    """

    # check if a menu script exists, and if it's in python
    if isinstance(parm, hou.StringParmTemplate) \
            or isinstance(parm, hou.MenuParmTemplate) \
            or isinstance(parm, hou.IntParmTemplate):
        if parm.itemGeneratorScriptLanguage() == hou.scriptLanguage.Python:
            menu_script = parm.itemGeneratorScript()
            file_name = parm.name()

            # menu scripts folder
            menu_script_folder = os.path.join(hda_folder_path, "menu_script")
            if not os.path.exists(menu_script_folder):
                os.mkdir(menu_script_folder)

            script_file_path = os.path.join(menu_script_folder, file_name + ".py")

            # check if file exists, if it does, don't update it
            if not os.path.exists(script_file_path):
                with open(script_file_path, 'w') as file_obj:
                    file_obj.write(menu_script)


def extract_py_scripts(definition, hda_folder_path):
    """
    Extracts the python scripts inside the scripts tab of the HDA file (if any).

    :param definition: HDA file definition.
    :param hda_folder_path: Scripts directory of the HDA file.
    """

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

            # check if file exists, if it does, don't update it
            if not os.path.exists(script_file_path):
                with open(script_file_path, 'w') as file_obj:
                    file_obj.write(py_script)


if __name__ == '__main__':
    main()
