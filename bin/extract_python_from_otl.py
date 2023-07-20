#! CM_NO_SGTK=1 /usr/bin/env hython

import sys
# import argparse
import shutil
import os
import hashlib
import json
import datetime as dt

"""
input for otl folder name hash = file path of otl
input for hda folder name hash = definition of hda
"""


def main():
    args = parse_args()
    txt_file_path = args[0]
    otl_file_paths = args[1]

    if txt_file_path[-4:] != ".txt":
        print("Given file is not a text file\n\n")

    print("Given text file path:" + txt_file_path + "\n\n")

    extract(txt_file_path, otl_file_paths)

    print("Script ran successfully\n\n")


def parse_args():
    # access individual paths from .txt file
    txt_file_path = sys.argv[1]
    with open(txt_file_path, 'r') as file:
        file_contents = file.read()

    file_paths = file_contents.split("\n")

    return txt_file_path, file_paths


def extract(txt_file_path, file_paths):
    # delete otl scripts folder if it already exists
    # delete(txt_file_path)

    # calculate the OTL scripts folder path from the file path
    txt_file_name = os.path.basename(txt_file_path)

    # the first line is the original.
    # otls_folder_path = txt_file_path[:-len(txt_file_name)]
    otls_folder_path = "/job/commsdev/ia_internship_2020_1/sandbox/asaravan/"

    # create a folder to store the scripts
    scripts_folder_exists = False
    scripts_folder_path = otls_folder_path + "otl_python_scripts/"

    # check if the script had already been run once, i.e. the scripts folder already exists.
    if os.path.exists(scripts_folder_path):
        scripts_folder_exists = True
    else:
        os.mkdir(scripts_folder_path)

    # iterate through all the OTLs

    # dict for storing and displaying the otl hash values
    otl_hash_dict = dict()
    otl_last_mod_time_dict = dict()

    for file_path in file_paths:
        if file_path[-4:] == ".hda":  # remove?
            if not os.path.exists(file_path):
                print("file path:" + file_path + " not valid, continuing to other HDAs\n\n")
                continue
            else:
                definitions = hou.hda.definitionsInFile(file_path)
                hou.hda.installFile(file_path)

                # Make a folder for each OTL
                otl_unique_name = make_unique_name(file_path)
                otl_folder_name = scripts_folder_path + otl_unique_name + "/"

                # checks if the script folder already exists, if it does,
                # get the last modified time of the otl folders.
                if scripts_folder_exists:
                    print("scripts folder already exists\n\n")
                    json_file_path = scripts_folder_path + "last_modified_time.json"

                    with open(json_file_path, "r") as file:
                        older_time_data = json.load(file)

                    if get_last_modified_time(file_path) != older_time_data[otl_unique_name]:
                        print(otl_unique_name + " was modified, updating it.\n\n")
                        shutil.rmtree(otl_folder_name)
                    else:
                        print("None of the OTLs were modified, proceeding as normal.\n\n")

                    if os.path.exists(otl_folder_name):
                        pass
                    else:
                        os.mkdir(otl_folder_name)

                # append to the otl hash dictionary
                otl_hash_dict[otl_unique_name] = file_path
                otl_last_mod_time_dict[otl_unique_name] = get_last_modified_time(file_path)

                # Make a folder for each HDA and extract python files
                # dict for storing and displaying the hda hash values
                hda_hash_dict = dict()

                for definition in definitions:
                    hda_unique_name = make_unique_name(definition)
                    hda_folder_name = otl_folder_name + hda_unique_name + "/"

                    if os.path.exists(hda_folder_name):
                        pass
                    else:
                        os.mkdir(hda_folder_name)

                    # extract python script and write to file
                    extract_py_and_write(definition, hda_folder_name)

                    # append to the hda hash dictionary
                    hda_hash_dict[
                        hda_unique_name] = definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()

                # write to json file
                j_hda_hash_dict = json.dumps(hda_hash_dict, indent=2)
                with open(otl_folder_name + "log.json", "w") as file:
                    file.write(j_hda_hash_dict)

    print("otl_python_scripts folder generated at:" + otls_folder_path + "\n\n")

    # write to json file
    j_otl_hash_dict = json.dumps(otl_hash_dict, indent=2)
    with open(scripts_folder_path + "log.json", "w") as file:
        file.write(j_otl_hash_dict)

    j_time_dict = json.dumps(otl_last_mod_time_dict, indent=2)
    with open(scripts_folder_path + "last_modified_time.json", "w") as file:
        file.write(j_time_dict)


def make_unique_name(var):
    """
    input for otl folder name hash = string of file path of otl
    input for hda folder name hash = string of definition of hda
    """
    hash_key = get_hash(var)

    # means var is an hda definition
    if isinstance(var, hou.HDADefinition):
        name = var.nodeTypeName()
        unique_name = str(name) + "_" + str(hash_key)

    # means var is a str (file path for an otl)
    else:
        otl_name = os.path.basename(var)
        unique_name = otl_name + "_" + str(hash_key)

    unique_name = unique_name.replace("/", "_").replace(" ", "_").replace(".", "_")
    return unique_name


def get_hash(var):
    """
    input for otl folder name hash = string of file path of otl
    input for hda folder name hash = string of definition of hda
    """
    a = hashlib.md5()
    a.update(str(var))
    hash_key = a.hexdigest()
    return hash_key


def get_last_modified_time(file_path):
    # modify_time = os.path.getmtime("/job/commsdev/ia_internship_2020_1/sandbox/asaravan/otl_python_scripts")
    modify_time = os.path.getmtime(file_path)
    modify_date = dt.datetime.fromtimestamp(modify_time)
    return str(modify_date)


def extract_py_and_write(definition, hda_folder_name):
    """
    :param definition: hda file definition
    :param hda_folder_name: string containing the folder name
    """

    # make 2 folders for the main scripts and the parameter callbacks
    # main python folder
    main_py_scripts_folder = hda_folder_name + "main_python_scripts/"
    if os.path.exists(main_py_scripts_folder):
        pass
    else:
        os.mkdir(main_py_scripts_folder)

    """
    filter out the python scripts and write
    to file in the respective directory
    """

    # pull out the python scripts in the scripts tab
    # iterate through each section

    definition_sections = definition.sections()
    efo = definition.extraFileOptions()

    for section in definition_sections:

        # check if it's a python script
        if section + "/IsPython" in efo.keys() and efo[section + "/IsPython"]:
            py_script = definition_sections[section].contents()
            file_name = definition_sections[section].name()

            # check and rectify file name for forward slash characters
            # print(type(file_name))
            file_name = file_name.replace('/', '_').replace('.', '_').replace(' ', '_')

            script_file_path = main_py_scripts_folder + file_name + ".py"

            # check if file exists, if it does, don't update it
            if os.path.exists(script_file_path):
                pass
            else:
                with open(script_file_path, 'w') as file:
                    file.write(py_script)

    # pull out the call back scripts from separate parameters
    # access each parameter
    ptg = definition.parmTemplateGroup()
    pt = ptg.parmTemplates()

    # exclude hdas with no parameters
    if len(pt) != 0:

        # iterate through each parameter
        for p in pt:

            # check if a menu script exists, and it's in python
            if isinstance(p, hou.StringParmTemplate) or isinstance(p, hou.MenuParmTemplate) or isinstance(p,
                                                                                                          hou.IntParmTemplate):
                if p.itemGeneratorScriptLanguage() == hou.scriptLanguage.Python:
                    menu_script = p.itemGeneratorScript()
                    file_name = p.name()

                    # menu scripts folder
                    menu_script_folder = hda_folder_name + "menu_script/"
                    if os.path.exists(menu_script_folder):
                        pass
                    else:
                        os.mkdir(menu_script_folder)

                    script_file_path = menu_script_folder + file_name + ".py"

                    # check if file exists, if it does, don't update it
                    if os.path.exists(script_file_path):
                        pass
                    else:
                        with open(script_file_path, 'w') as file:
                            file.write(menu_script)

            # check if a callback script exists, and it's in python
            if p.scriptCallbackLanguage() == hou.scriptLanguage.Python and len(p.scriptCallback()) > 0:

                # parameter callback folder
                parameter_callback_folder = hda_folder_name + "parameter_callbacks/"
                if os.path.exists(parameter_callback_folder):
                    pass
                else:
                    os.mkdir(parameter_callback_folder)

                callback_py_script = p.scriptCallback()
                script_name = p.name()
                script_file_path = parameter_callback_folder + script_name + ".py"

                # check if file exists, if it does, don't update it
                if os.path.exists(script_file_path):
                    pass
                else:
                    with open(script_file_path, 'w') as file:
                        file.write(callback_py_script)


if __name__ == '__main__':
    main()
