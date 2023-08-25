import os
import json
import mock
import shutil
import commslib.temp as cm
import test_extract_python_from_otl as tepfo
import extract_python_from_otl as epfo

# If the test OTLs have been modified, the test data has to be generated again.


def main():
    # Generates test data for input "otl_list.txt" and "sky_scraper.hda"
    generate_test_data(tepfo.get_test_otls_paths(), "multiple_otls.json")
    generate_test_data(tepfo.get_sky_scraper_otl_path(), "sky_scraper_otl.json")


def generate_test_data(otl_file_paths, comparison_data_file_name):
    """
    Generates test data in the "comparison data" folder so that it can be used
    for data comparison while running the integration test.

    :param otl_file_paths: list Test data otl file paths
    :param comparison_data_file_name: str comparison data json file name
    """

    with mock.patch("extract_python_from_otl.get_hash", side_effect=tepfo.hash_side_effect):

        temp_folder_name = "otl_python_extraction_tool_test_data"
        temp_folder_path = cm.make_directory(temp_folder_name)

        assert temp_folder_name in temp_folder_path

        folder_name = "otl_scripts_folder"
        epfo.extract_python(otl_file_paths, temp_folder_path, folder_name)

    file_path_to_output_data = tepfo.get_comparison_data_dir()
    tool_test_results_file_path = temp_folder_path

    folder_tree_dict = tepfo.generate_folder_tree_dict(tool_test_results_file_path)

    with open(os.path.join(file_path_to_output_data, comparison_data_file_name), "w") as file_obj:
        json.dump(folder_tree_dict, file_obj, indent=2)

    # clean up
    if os.path.exists(temp_folder_path):
        shutil.rmtree(temp_folder_path)


if __name__ == '__main__':
    main()
