import json
import psycopg2
from psycopg2.extras import DictCursor
import sys
import os
import random
import copy
import time
from datetime import datetime

def connect_db():
    """Connect to the PostgreSQL database."""
    return psycopg2.connect(
        dbname='invenio',
        user='invenio',
        password='dbpass123',
        host='localhost',
        port=25401,
    )

def remove_xsd_prefix(jpcoar_lists):
    """Remove xsd prefix."""
    jpcoar_copy = {}
    def remove_prefix(jpcoar_src, jpcoar_dst):
        for key, value in jpcoar_src.items():
            if key == 'type':
                jpcoar_dst[key] = value
                continue
            jpcoar_dst[key.split(':').pop()] = {}
            if isinstance(value, dict):
                remove_prefix(value, jpcoar_dst[key.split(':').pop()])
    remove_prefix(jpcoar_lists, jpcoar_copy)
    return jpcoar_copy

def get_db_json(table, columns, where=None):
    """
    Get JSON data from database table.
    Args:
        table (str): Table name.
        columns (str or list): Column name(s) to fetch.
        where (str): Optional WHERE clause.
    Returns:
        dict or list: Fetched JSON data.
    """
    conn = connect_db()
    cur = conn.cursor(cursor_factory=DictCursor)
    if isinstance(columns, list):
        col_str = ", ".join(columns)
    else:
        col_str = columns
    query = f"SELECT {col_str} FROM {table}"
    if where:
        query += f" WHERE {where}"
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return None
    if len(rows) == 1:
        row = rows[0]
        if isinstance(columns, str) and ',' not in columns and not isinstance(columns, list):
            data = row[columns]
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            return data
        return dict(row)
    else:
        return [dict(r) for r in rows]

def get_property_keys(schema):
    """
    Get property keys from item schema.
    Args:
        schema (dict): Item schema.
    Returns:
        dict: Property keys with list of keys for each property.
    """
    def collect_keys(prop, prefix=""):
        """Recursively collect keys from schema property."""
        keys = []
        if prop.get("type") == "object" and "properties" in prop:
            for k, v in prop["properties"].items():
                keys.extend(collect_keys(v, f"{prefix}{k}." if prefix else f"{k}."))
        elif prop.get("type") == "array" and "items" in prop:
            items = prop["items"]
            if items.get("type") in ("object", "array"):
                keys.extend(collect_keys(items, prefix))
            else:
                keys.append(prefix[:-1] if prefix.endswith('.') else prefix)
        else:
            keys.append(prefix[:-1] if prefix.endswith('.') else prefix)
        return keys

    result = {}
    properties = schema.get("properties", {})
    for prop_name, prop_value in properties.items():
        if prop_name == "pubdate":
            result[prop_name] = [prop_name]
        else:
            result[prop_name] = collect_keys(prop_value)
    return result

def find_attribute_leaves(node, path=()):
    """
    Find leaf nodes that have attributes anywhere in the schema.
    Args:
        node (dict): Current node in schema.
        path (tuple): Current path of keys.
    Returns:
        list: List of tuples (leaf_path, attribute_names).
    """
    def get_attr_names(n):
        if not isinstance(n, dict):
            return []
        names = []
        attrs = n.get("attributes", [])
        names += [attr.get("name") for attr in attrs if isinstance(attr, dict) and "name" in attr]
        if "type" in n and isinstance(n["type"], dict):
            names += get_attr_names(n["type"])
        return names

    leaves = []
    if not isinstance(node, dict):
        return []
    keys = [k for k in node.keys() if k != "type"]
    if not keys:
        attr_names = get_attr_names(node)
        if attr_names:
            leaves.append((path, attr_names))
        return leaves
    for k in keys:
        val = node[k]
        if isinstance(val, dict):
            leaves.extend(find_attribute_leaves(val, path + (k,)))
    return leaves

def add_empty_mappings(mapping_item):
    """
    Add empty string mappings for fixed mapping types.
    Args:
        mapping_item (dict): Mapping item to add empty mappings to.
    """
    mapping_item["display_lang_type"] = ""
    mapping_item["junii2_mapping"] = ""
    mapping_item["lido_mapping"] = ""
    mapping_item["spase_mapping"] = ""

def save_body(body, output_dir, output_file_name):
    """
    Save body to JSON file.
    Args:
        body (dict): Body to save.
        output_dir (str): Output directory.
        output_file_name (str): Output file name.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    base_name, ext = os.path.splitext(output_file_name)
    if not base_name.endswith("_1"):
        base_name += "_1"
    output_file_name = base_name + ext
    output_path = os.path.join(output_dir, output_file_name)
    idx = 2
    while os.path.exists(output_path):
        output_path = os.path.join(output_dir, f"{base_name[:-2]}_{idx}{ext}")
        idx += 1
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

def set_nested_mapping(mapping_dict, leaf_node, value, attr_dict=None):
    """
    Set value and attributes in nested mapping dict.
    Args:
        mapping_dict (dict): Mapping dictionary to set values in.
        leaf_node (str): Dot-separated path to the leaf node.
        value (str): Value to set at the leaf node.
        attr_dict (dict): Optional attributes to set at the leaf node.
    """
    keys = leaf_node.split('.')
    current_dict = mapping_dict
    for k in keys[:-1]:
        current_dict = current_dict.setdefault(k, {})
    current_dict[keys[-1]] = {"@value": value}
    if attr_dict:
        current_dict[keys[-1]]["@attributes"] = attr_dict

def build_schema_list(schema_mt):
    """
    Build schema list from mapping type schema.
    Args:
        schema_mt (dict): Mapping type schema.
    Returns:
        result (list): List of tuples (leaf_path, attribute_names).
    """
    leaves = find_attribute_leaves(schema_mt)
    result = []
    for leaf, attr_names in leaves:
        result.append((".".join(leaf), attr_names))
    return result

def build_schema_leaf_attr_list(schema_mt):
    """
    Build schema leaf attribute list from mapping type schema.
    Args:
        schema_mt (dict): Mapping type schema.
    Returns:
        result (list): List of tuples (leaf_path, attribute_name).
    """
    leaves = find_attribute_leaves(schema_mt)
    result = []
    for leaf, attr_names in leaves:
        leaf_path = ".".join(leaf)
        result.append((leaf_path, "@value"))
        for attr in attr_names:
            result.append((leaf_path, attr))
    return result

def create_all_schema_mappings(required_types, mapping_type_schemas, db_item_keys, property_keys, item_type_id, output_dir):
    """
    Create mapping body test files covering all schema leaves.
    Args:
        required_types: list of mapping types
        mapping_type_schemas(dict): mapping type schemas
        db_item_keys(list): item keys from database
        property_keys(dict): property keys
        item_type_id(int): item type ID
        output_dir: str
    """
    for mapping_type in required_types:
        schema_mt = mapping_type_schemas.get(mapping_type)
        if not schema_mt:
            continue
        schema_leaf_attr_list = build_schema_leaf_attr_list(schema_mt)
        schema_leaf_attr_copy = schema_leaf_attr_list.copy()
        file_idx = 1

        while schema_leaf_attr_copy:
            mapping = {}
            for item in db_item_keys:
                value_keys = property_keys.get(item, [])
                mapping_dict = {}
                v_idx = 0
                schema_leaf_attr_inner = schema_leaf_attr_copy.copy()
                for leaf_path, attr in schema_leaf_attr_inner:
                    if v_idx >= len(value_keys):
                        break
                    keys = leaf_path.split('.')
                    current_dict = mapping_dict
                    for k in keys[:-1]:
                        current_dict = current_dict.setdefault(k, {})
                    if attr == "@value":
                        current_dict[keys[-1]] = current_dict.get(keys[-1], {})
                        current_dict[keys[-1]]["@value"] = value_keys[v_idx]
                    else:
                        current_dict[keys[-1]] = current_dict.get(keys[-1], {})
                        current_dict[keys[-1]].setdefault("@attributes", {})
                        current_dict[keys[-1]]["@attributes"][attr] = value_keys[v_idx]
                    v_idx += 1
                    schema_leaf_attr_copy.pop(0)
                    if not schema_leaf_attr_copy:
                        break
                mapping[item] = {mt: "" for mt in required_types}
                mapping[item][mapping_type] = mapping_dict if mapping_dict else ""
                add_empty_mappings(mapping[item])

            body = {
                "item_type_id": item_type_id,
                "mapping": mapping,
                "mapping_type": mapping_type
            }
            save_body(body, output_dir, f"mapping_all_schemalist_{mapping_type}.json")

def create_dupulicate_metadata(current_dict, target_value):
    """
    Function to generate a mapping that causes a duplication error.
    Args:
        current_dict(dict): Current mapping dictionary.
        target_value(str): The value to property.
    Returns:
        dict: New mapping dictionary with duplication.
    """
    if not isinstance(current_dict, dict):
        return current_dict
    new_dict = {}
    for key, val in current_dict.items():
        if key == "@attributes" and isinstance(val, dict) and target_value in val.values():
            continue
        if isinstance(val, dict) and val.get("@value") == target_value:
            continue
        if isinstance(val, dict):
            child = create_dupulicate_metadata(val, target_value)
            if child is not None and (not isinstance(child, dict) or child):
                new_dict[key] = child
        else:
            new_dict[key] = val
    return new_dict if new_dict else None

def create_mapping_body(required_types, mapping_type_schemas, db_item_keys, property_keys, item_type_id, output_dir, mode="random", same_item_keys=[]):
    """
    Create mapping body test files.
    Args:
        required_types(list): list of mapping types
        mapping_type_schemas(dict): mapping type schemas
        db_item_keys(list): item keys from database
        property_keys(dict): property keys
        item_type_id(int): item type ID
        output_dir(str): output directory
        mode(str): "random" or "duplicate"
        same_item_keys(list): list of item keys to duplicate in "duplicate" mode
    """
    item1 = None
    item2 = None
    file_name = "success"
    if mode == 'duplicate':
        item1 = same_item_keys[0]
        item2 = same_item_keys[1]
        file_name = mode
    
    # mapping_typeごとにファイルを出力
    for output_mapping_type in required_types:
        mapping = {}
        # mapping_typeごとに使用済みスキーマセットを用意(想定外の重複防止)
        used_leaves_global = {mt: set() for mt in required_types}
        for item in db_item_keys:
            value_keys = property_keys.get(item, [])
            if item == item2 and mode == 'duplicate':
                item1_copy = copy.deepcopy(mapping[item1])
                mapping[item] = create_dupulicate_metadata(item1_copy, value_keys[1])
                continue
            mapping[item] = {}
            for mapping_type in required_types:
                schema_mt = mapping_type_schemas.get(mapping_type)
                if not schema_mt:
                    mapping[item][mapping_type] = ""
                    continue
                schema_list = build_schema_list(schema_mt)
                schema_list_copy = schema_list.copy()
                random.shuffle(schema_list_copy)
                mapping_dict = {}
                v_idx = 0
                # 使用済みスキーマを管理
                used_leaves = used_leaves_global[mapping_type]
                for _ in range(len(value_keys)):
                    available_leaves = [s for s in schema_list_copy if s[0] not in used_leaves]
                    if not available_leaves:
                        break
                    leaf_node, attr_names = random.choice(available_leaves)
                    used_leaves.add(leaf_node)
                    if attr_names and (len(value_keys) - v_idx) >= len(attr_names) + 1:
                        attr_dict = {}
                        for i, attr in enumerate(attr_names):
                            attr_dict[attr] = value_keys[v_idx + i + 1]
                        set_nested_mapping(mapping_dict, leaf_node, value_keys[v_idx], attr_dict)
                        v_idx += len(attr_names) + 1
                    else:
                        set_nested_mapping(mapping_dict, leaf_node, value_keys[v_idx])
                        v_idx += 1
                    if v_idx >= len(value_keys):
                        break
                mapping[item][mapping_type] = mapping_dict if mapping_dict else ""
            add_empty_mappings(mapping[item])

        body = {
            "item_type_id": item_type_id,
            "mapping": mapping,
            "mapping_type": output_mapping_type
        }
        save_body(body, output_dir, f"mapping_{file_name}_{output_mapping_type}.json")

def create_error_files(required_types, item_type_id, output_dir):
    """
    Create error test files.
    Args:
        required_types(list): list of mapping types
        item_type_id(int): item type ID
        output_dir(str): output directory
    """
    # item_type_idが不正な値(文字列、null)
    for special_id in ["abc", "null"]:
        for mapping_type in required_types:
            body = {
                "item_type_id": None if special_id == "null" else special_id,
                "mapping": {},
                "mapping_type": mapping_type
            }
            save_body(body, output_dir, f"mapping_{special_id}_{mapping_type}.json")

    # item_type_idキー欠損
    for mapping_type in required_types:
        body_noid = {
            "mapping": {},
            "mapping_type": mapping_type
        }
        save_body(body_noid, output_dir, f"mapping_noid_{mapping_type}.json")

    # mapping_typeキー欠損
    body_noid = {
        "item_type_id": item_type_id,
        "mapping": {}
    }
    save_body(body_noid, output_dir, f"mapping_no_mapping_type.json")

def main():
    """
    Main function to generate request body test files.
    Usage: python generate_request_body.py <item_type_id> [meta_id1 meta_id2]    
    """
    start_time = time.time()
    print(f"テストデータ生成開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    total_files_before = count_json_files("request_params/item_type_mapping/test_data")

    required_types = ["ddi_mapping", "lom_mapping", "jpcoar_v1_mapping", "jpcoar_mapping", "oai_dc_mapping"]
    test_roles = ["sysadmin", "repoadmin", "comadmin", "contributor", "user", "guest"]
    argc = len(sys.argv)
    if argc < 2:
        print("Usage: python generate_request_body.py <item_type_id> [meta_id1 meta_id2]")
        sys.exit(1)
    item_type_id_arg = sys.argv[1]
    try:
        item_type_id = int(item_type_id_arg)
    except ValueError:
        print("Error: item_type_id must be an integer and exist in the database.")
        sys.exit(1)

    exists = get_db_json("item_type", "id", f"id = {item_type_id}")
    if not exists:
        print(f"Error: item_type_id {item_type_id} does not exist in item_type table.")
        sys.exit(1)

    schemas_raw = get_db_json("oaiserver_schema", ["xsd", "schema_name"])
    mapping_type_schemas = {}
    if schemas_raw:
        for row in schemas_raw:
            mapping_type = row.get("schema_name")
            xsd = row.get("xsd")
            if isinstance(xsd, str):
                xsd = json.loads(xsd)
            mapping_type_schemas[mapping_type] = remove_xsd_prefix(xsd)

    schema = get_db_json("item_type", "schema", f"id = {item_type_id}")
    property_keys = get_property_keys(schema)

    # メタデータID一覧
    mapping_raw = get_db_json("item_type_mapping", "mapping", f"item_type_id = {item_type_id}")
    if not mapping_raw:
        raise Exception(f"mapping not found for item_type_id={item_type_id}")
    while isinstance(mapping_raw, list):
        if not mapping_raw:
            raise Exception(f"mapping is empty for item_type_id={item_type_id}")
        mapping_raw = mapping_raw[0]
    if isinstance(mapping_raw, dict) and "mapping" in mapping_raw:
        mapping_raw = mapping_raw["mapping"]

    # メタデータ一覧の整理
    def set_db_keys(k):
        if k == "pubdate":
            return (0, "")
        elif k == "system_file":
            return (1, k)
        elif k.startswith("system_identifier"):
            return (2, k)
        elif k.startswith("item_"):
            # 数値部分を昇順でソート
            try:
                num = int(k.split("_")[1])
            except Exception:
                num = 0
            return (3, num)
        else:
            return (4, k)
    db_item_keys = sorted(list(mapping_raw.keys()), key=set_db_keys)

    for role in test_roles:
        print(f"{role}のテストデータの生成を開始します。")
        # 各スキーマリストを使いきる正常系データ生成する
        output_dir = f"request_params/item_type_mapping/test_data/{role}/all_schema_mappings/"
        create_all_schema_mappings(required_types, mapping_type_schemas, db_item_keys, property_keys, item_type_id, output_dir)

        # 処理が成功するjsonデータを生成する(値はランダムでかつ他と重複しない)
        output_dir = f"request_params/item_type_mapping/test_data/{role}/success/"
        if argc >= 5:
            try:
                loop_count = int(sys.argv[4])
            except Exception:
                loop_count = 1
        else:
            loop_count = 1
        for i in range(loop_count):
            create_mapping_body(
                required_types, mapping_type_schemas, db_item_keys, property_keys,
                item_type_id, output_dir, mode="random"
            )
            
        # 指定したメタデータidだけ重複するjsonデータを生成する(指定メタデータ以外の値はランダムでかつ他と重複しない)
        if argc < 4:
            print("Usage: python generate_request_body.py <item_type_id> [meta_id1 meta_id2]")
        else:
            output_dir = f"request_params/item_type_mapping/test_data/{role}/duplicate/"
            same_item_keys = sorted(sys.argv[2:4], reverse=False)
            create_mapping_body(required_types, mapping_type_schemas, db_item_keys, property_keys, item_type_id, output_dir, mode="duplicate", same_item_keys=same_item_keys)
        
        # 異常系用テストファイルを生成する
        output_dir = f"request_params/item_type_mapping/test_data/{role}/error/"
        create_error_files(required_types, item_type_id, output_dir)
        print(f"{role}のテストデータの生成が終了しました。")
    
    total_files_after = count_json_files("request_params/item_type_mapping/test_data")
    elapsed = time.time() - start_time
    print(f"テストデータ生成終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"所要時間: {int(elapsed // 60)}分 {int(elapsed % 60)}秒")
    print(f"生成したJSONファイル数: {total_files_after - total_files_before}件")

def count_json_files(root_dir):
    count = 0
    for dirpath, _, filenames in os.walk(root_dir):
        count += sum(1 for f in filenames if f.endswith('.json'))
    return count

if __name__ == "__main__":
    main()