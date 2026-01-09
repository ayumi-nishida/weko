import pytest
from tavern.core import run

def get_success_json_file_list():
    import os
    dir_path = "../../tavern/request_params/item_type_mapping/test_data/sysadmin/success"
    return [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.endswith(".json")
    ]

@pytest.mark.parametrize("success_filename", get_success_json_file_list())
def test_mapping_success(success_filename):
    run("test/tavern/test/test_w2025-28_3.tavern.yaml", {"success_filename": success_filename})

def get_error_json_file_list(prefix):
    import os
    dir_path = "../../tavern/request_params/item_type_mapping/test_data/sysadmin/error"
    return [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.startswith(prefix) and f.endswith(".json")
    ]

@pytest.mark.parametrize("error_abc", get_error_json_file_list("mapping_abc_"))
def test_mapping_error_abc(error_abc):
    run("test/tavern/test/test_w2025-28_3.tavern.yaml", {"error_abc": error_abc})

@pytest.mark.parametrize("error_null", get_error_json_file_list("mapping_null_"))
def test_mapping_error_null(error_null):
    run("test/tavern/test/test_w2025-28_3.tavern.yaml", {"error_null": error_null})

@pytest.mark.parametrize("error_noid", get_error_json_file_list("mapping_noid_"))
def test_mapping_error_noid(error_noid):
    run("test/tavern/test/test_w2025-28_3.tavern.yaml", {"error_noid": error_noid})

def get_duplicate_json_file_list():
    import os
    dir_path = "../../tavern/request_params/item_type_mapping/test_data/sysadmin/duplicate"
    return [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.endswith(".json")
    ]

@pytest.mark.parametrize("duplicate_filename", get_duplicate_json_file_list())
def test_mapping_duplicate(duplicate_filename):
    run("test/tavern/test/test_w2025-28_3.tavern.yaml", {"duplicate_filename": duplicate_filename})
