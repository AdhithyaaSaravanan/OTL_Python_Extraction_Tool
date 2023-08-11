import os
import json
import test_extract_python_from_otl as tepfo

# If the test OTLs have been modified, the test data has to be generated again.


def generate_test_data(data_name):

    file_path_to_output_data = tepfo.get_file_path_to_test_json_files()
    tool_test_results_file_path = os.path.join(tepfo.get_test_data_dir(), "tool_test_results", data_name)

    folder_tree_dict = tepfo.generate_folder_tree_dict(tool_test_results_file_path)

    j_test_result_info = json.dumps(folder_tree_dict, indent=4)
    with open(os.path.join(file_path_to_output_data, data_name + ".json"), "w") as file_obj:
        file_obj.write(j_test_result_info)


generate_test_data("sky_scraper_otl")
generate_test_data("multiple_otls")
