import os
import json
import mock
import shutil
import commslib.temp as cm
import test_extract_python_from_otl as tepfo
import extract_python_from_otl as epfo

# If the test OTLs have been modified, the test data has to be generated again.


def generate_test_data(otl_data):
    # TODO: Missing docstring

    with mock.patch("extract_python_from_otl.get_hash", side_effect=tepfo.hash_side_effect):

        temp_folder_name = "otl_python_extraction_tool_test_data"
        temp_folder_path = cm.make_directory(temp_folder_name)

        assert temp_folder_name in temp_folder_path

        folder_name = "otl_scripts_folder"
        file_paths = tepfo.get_test_otls_paths(otl_data)

        epfo.extract_python(file_paths, temp_folder_path, folder_name)

        file_path_to_output_data = tepfo.get_file_path_to_test_json_files()
        tool_test_results_file_path = temp_folder_path

        # If input is a txt file, name the .json file "multiple_otls"
        # TODO: Should this be `otl_data.endswith(".txt")`?
        if ".txt" in otl_data:
            data_name = "multiple_otls.json"
        # If it's a single otl, name the .json file "sky_scraper_otl"
        else:
            # TODO: Why is this name being hard coded? You should be driving this from a function argument
            data_name = "sky_scraper_otl.json"

        folder_tree_dict = tepfo.generate_folder_tree_dict(tool_test_results_file_path)

        # TODO: Use `json.dump` instead of using a string intermediary
        j_test_result_info = json.dumps(folder_tree_dict, indent=4)
        with open(os.path.join(file_path_to_output_data, data_name), "w") as file_obj:
            file_obj.write(j_test_result_info)

        # clean up
        if os.path.exists(temp_folder_path):
            shutil.rmtree(temp_folder_path)

# TODO: You should wrap these two lines in a "if __name__ == '__main__':" so that it doesn't get
#    executed if it gets imported
# TODO: This is a bit weird being able to pass an HDA or a text file to the same function like this. Consider
#    either using separate arguments (e.g. an HDA argument and a text file argument), or use two different functions.
generate_test_data("sky_scraper.hda")
generate_test_data("otl_list.txt")
