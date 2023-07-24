#!/usr/bin/env hython

# CM_NO_SGTK=1

# import sys
import argparse
import shutil
import os
import hashlib
import json
import datetime as dt


def main():

    parser = argparse.ArgumentParser(description="extracts python scripts from a given list of otls")

    # text file input
    parser.add_argument("-opl", "--otl_paths_list", type=str,
                        help="A text file with a list of otl pathways.")

    # otl input
    parser.add_argument("-otl", "--otlUpdate", type=str, nargs='*',
                        help="Pathway to an otl.")

    # folder name input
    parser.add_argument("-n", "--name", type=str, default="otl_scripts_folder", help="A name for the generated "
                                                                                     "scripts folder.")

    # folder directory input
    parser.add_argument("-d", "--directory", type=str, help="A directory for the generated scripts folder.")

    # parse args
    args = parser.parse_args()

    if not args.otl_paths_list and not args.otlUpdate:
        parser.error("provide a text file or a specific otl path to generate the scripts folder.")

    # folder directory
    if args.directory:
        if args.directory[-1] == "/":
            otls_folder_path = args.directory
        else:
            otls_folder_path = args.directory + "/"

    # if text file is given, default folder directory is the same is the text file,
    # else it is the same as the tool.
    if not args.directory:
        if args.otl_paths_list:
            txt_file_name = os.path.basename(args.otl_paths_list)
            otls_folder_path = args.otl_paths_list[:-len(txt_file_name)]
        else:
            # the olts_folder_path is the same as the text file.
            this_file_path = os.path.abspath(__file__)
            this_file_name = os.path.basename(this_file_path)
            otls_folder_path = this_file_path[:-len(this_file_name)]

    # folder name
    if args.name:
        folder_name = args.name
    else:
        folder_name = "otl_python_scripts"

    if args.otl_paths_list:
        txt_file_path = args.otl_paths_list

        # access individual paths from .txt file
        with open(txt_file_path, 'r') as file:
            file_contents = file.read()

        otl_file_paths = file_contents.split("\n")

        if txt_file_path[-4:] != ".txt":
            parser.error("Given file is not a text file\n\n")

        print("\n\nGiven text file path:" + txt_file_path + "\n\n")

        extract(otl_file_paths, otls_folder_path, folder_name)

    if args.otlUpdate:
        extract(args.otlUpdate, otls_folder_path, folder_name)

    print("Script ran successfully\n\n")


def extract(file_paths, otls_folder_path, name):
    """
    :param str otls_folder_path: a text file containing a list of pathways to otls
    :param list file_paths: a list of pathways to otls
    :param str name: name of the generated folder
    """

    """
    function to iterate through all the otls and extract all python scripts inside.
    """

    # create a folder to store the scripts
    scripts_folder_exists = False
    scripts_folder_path = otls_folder_path + name + "/"

    # check if the script had already been run once, i.e. the scripts folder already exists.
    if os.path.exists(scripts_folder_path):
        scripts_folder_exists = True
    else:
        os.mkdir(scripts_folder_path)

    # dict for storing and displaying the otl hash values
    otl_hash_dict = dict()

    # dict for storing and displaying the last modified time of the otls
    # otl_last_mod_time_dict = dict()

    # iterate through the file paths
    for file_path in file_paths:

        # check if it's an hda file
        if file_path[-4:] == ".hda":

            # check if path is valid
            if not os.path.exists(file_path):
                print("file path:" + file_path + " not valid, continuing to other HDAs\n\n")
                continue
            else:
                definitions = hou.hda.definitionsInFile(file_path)
                hou.hda.installFile(file_path)

                # Make a folder for each OTL
                otl_unique_name = make_unique_name(file_path)
                otl_folder_path = scripts_folder_path + otl_unique_name + "/"

                # checks if a scripts folder was already generated, if it was,
                # get the last modified time of the otl folders.
                if scripts_folder_exists:
                    # print("scripts folder already exists\n\n")
                    json_file_path = scripts_folder_path + "log.json"

                    with open(json_file_path, "r") as file:
                        older_time_data = json.load(file)

                    # if any of the otls were modified, update the scripts inside them
                    # (delete the old one and generate a new one)
                    if get_last_modified_time(file_path) != older_time_data[otl_unique_name][1]:
                        print(otl_unique_name + " was modified, updating it.\n\n")
                        shutil.rmtree(otl_folder_path)
                    else:
                        # print("None of the OTLs were modified, proceeding as normal.\n\n")
                        pass

                if os.path.exists(otl_folder_path):
                    pass
                else:
                    os.mkdir(otl_folder_path)

                # append to the otl hash dictionary
                otl_hash_dict[otl_unique_name] = file_path, "last_mod_time: " + get_last_modified_time(file_path)

                # append to the otl last modified time dictionary
                # otl_last_mod_time_dict[otl_unique_name] = get_last_modified_time(file_path)

                # dict for storing and displaying the hda hash values
                hda_hash_dict = dict()

                # Make a folder for each HDA and extract the python files inside
                for definition in definitions:
                    hda_unique_name = make_unique_name(definition)
                    hda_folder_path = otl_folder_path + hda_unique_name + "/"

                    if os.path.exists(hda_folder_path):
                        pass
                    else:
                        os.mkdir(hda_folder_path)

                    # extract python script and write to file
                    extract_py_and_write(definition, hda_folder_path)

                    # append to the hda hash dictionary
                    hda_hash_dict[
                        hda_unique_name] = definition.nodeTypeCategory().name() + "/" + definition.nodeTypeName()

                # write the hda hash dict to a json file
                j_hda_hash_dict = json.dumps(hda_hash_dict, indent=2)
                with open(otl_folder_path + "log.json", "w") as file:
                    file.write(j_hda_hash_dict)

    print(name + " folder generated at:" + otls_folder_path + "\n\n")

    # write the otl hash dict to a json file
    j_otl_hash_dict = json.dumps(otl_hash_dict, indent=2)
    with open(scripts_folder_path + "log.json", "w") as file:
        file.write(j_otl_hash_dict)
    #
    # # write the otl last modified time dict to a json file
    # j_time_dict = json.dumps(otl_last_mod_time_dict, indent=2)
    # with open(scripts_folder_path + "last_modified_time.json", "w") as file:
    #     file.write(j_time_dict)


def make_unique_name(var):
    """
    :param var: either a str(file path of an otl) or a hda definition
    :return: a hashed name of an otl or an hda
    """

    """
    input for otl folder name hash = string of file path of otl
    input for hda folder name hash = definition of hda
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
    :param var: either a str(file path of an otl) or a hda definition
    :return: a hash key
    """

    """
    input for otl folder name hash = string of file path of otl
    input for hda folder name hash = definition of hda
    """
    a = hashlib.md5()
    a.update(str(var))
    hash_key = a.hexdigest()
    return hash_key


def get_last_modified_time(file_path):
    """
    :param str file_path: file path to an hda
    :return: string of the last modified time of the hda
    """

    modify_time = os.path.getmtime(file_path)
    modify_date = dt.datetime.fromtimestamp(modify_time)
    return str(modify_date)


def extract_py_and_write(definition, hda_folder_path):
    """
    :param definition: hda file definition
    :param hda_folder_path: string containing the folder name
    """

    # making a folder for the main python scripts
    main_py_scripts_folder = hda_folder_path + "main_python_scripts/"
    if os.path.exists(main_py_scripts_folder):
        pass
    else:
        os.mkdir(main_py_scripts_folder)

    """
    filter out the python scripts and write
    to file in the respective directory
    """

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

            # check if a menu script exists, and if it's in python
            if isinstance(p, hou.StringParmTemplate) or isinstance(p, hou.MenuParmTemplate) or isinstance(p, hou.IntParmTemplate):
                if p.itemGeneratorScriptLanguage() == hou.scriptLanguage.Python:
                    menu_script = p.itemGeneratorScript()
                    file_name = p.name()

                    # menu scripts folder
                    menu_script_folder = hda_folder_path + "menu_script/"
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

            # check if a callback script exists, and if it's in python
            if p.scriptCallbackLanguage() == hou.scriptLanguage.Python and len(p.scriptCallback()) > 0:

                # parameter callback folder
                parameter_callback_folder = hda_folder_path + "parameter_callbacks/"
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
