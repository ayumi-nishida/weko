import os
import json
import psycopg2
from psycopg2.extras import DictCursor

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
    """Get JSON data from database table."""
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

def find_attribute_leaves(node, path=()):
    """
    Find leaves with attributes in the schema node.
    Args:
        node (dict): The schema node.
        path (tuple): The current path in the schema.
    Returns:
        list: A list of tuples containing the leaf path and attribute names.
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
            leaves.append((".".join(path), tuple(attr_names)))
        return leaves
    for k in keys:
        val = node[k]
        if isinstance(val, dict):
            leaves.extend(find_attribute_leaves(val, path + (k,)))
    return leaves

def collect_used_leaves_detailed(target_dir, mapping_type, schema_leaves):
    result = {}
    for leaf, attr_names in schema_leaves:
        result[leaf] = {
            "@value": set(),
            "@attributes": {attr: set() for attr in attr_names}
        }
    for fname in os.listdir(target_dir):
        if not fname.endswith(".json"):
            continue
        # ディレクトリ名で判定
        if "success" in target_dir:
            if not fname.startswith(f"mapping_success_{mapping_type}"):
                continue
        else:
            if not fname.startswith(f"mapping_all_schemalist_{mapping_type}"):
                continue
        fpath = os.path.join(target_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        mapping = data.get("mapping", {})
        for item in mapping.values():
            mt_dict = item.get(mapping_type, {})
            def walk(d, path=[]):
                if not isinstance(d, dict):
                    return
                for k, v in d.items():
                    current_path = ".".join(path + [k])
                    # @value
                    if isinstance(v, dict) and "@value" in v:
                        if current_path in result:
                            result[current_path]["@value"].add(fname)
                    # @attributes
                    if isinstance(v, dict) and "@attributes" in v:
                        for attr in v["@attributes"]:
                            if current_path in result and attr in result[current_path]["@attributes"]:
                                result[current_path]["@attributes"][attr].add(fname)
                    walk(v, path + [k])
            walk(mt_dict)
    return result

def get_unique_log_path(output_dir):
    """
    Get a unique log file path by appending an index if the file already exists.
    Args:
        output_dir (str): The desired log file path.
    Returns:
        str: A unique log file path.
    """
    if not os.path.exists(output_dir):
        return output_dir
    base, ext = os.path.splitext(output_dir)
    idx = 1
    while True:
        new_path = f"{base}_{idx}{ext}"
        if not os.path.exists(new_path):
            return new_path
        idx += 1

def append_usage_details(details, mapping_type, schema_leaves, usage, title="使用ファイル", only_unused=False):
    """
    Append usage details to the details list.
    Args:
        details (list): The list to append details to.
        mapping_type (str): The mapping type.
        schema_leaves (list): The list of schema leaves.
        usage (dict): The usage data.
        title (str): The title for the section. 
        only_unused (bool): Whether to include only unused items.
    """
    unused_found = False
    lines = [f"=== {mapping_type} {title} ===\n"]
    for leaf, attr_names in schema_leaves:
        leaf_unused = False
        lines.append(f"{leaf}\n")
        files = usage[leaf]["@value"]
        if files:
            lines.append(f"  @value: {', '.join(sorted(files))}\n")
        else:
            lines.append(f"  @value: [未使用]\n")
            unused_found = True
            leaf_unused = True
        lines.append(f"  @attributes: {{\n")
        for attr in attr_names:
            attr_files = usage[leaf]["@attributes"][attr]
            if attr_files:
                lines.append(f"    '{attr}': {', '.join(sorted(attr_files))}\n")
            else:
                lines.append(f"    '{attr}': [未使用]\n")
                unused_found = True
                leaf_unused = True
        lines.append(f"  }}\n\n")
    # only_unused=True かつ未使用項目が1つでもあれば出力
    if only_unused:
        if unused_found:
            details.extend(lines)
    else:
        details.extend(lines)

def main():
    """Main function to verify schema usage and log details."""
    schemas_raw = get_db_json("oaiserver_schema", ["xsd", "schema_name"])
    mapping_type_schemas = {}
    if schemas_raw:
        for row in schemas_raw:
            mapping_type = row.get("schema_name")
            xsd = row.get("xsd")
            if isinstance(xsd, str):
                xsd = json.loads(xsd)
            mapping_type_schemas[mapping_type] = remove_xsd_prefix(xsd)

    test_roles = ["sysadmin", "repoadmin", "comadmin", "contributor", "user", "guest"]
    for role in test_roles:
        target_dir_list = [f"request_params/item_type_mapping/test_data/{role}/all_schema_mappings/", f"request_params/item_type_mapping/test_data/{role}/success/"]
        for target_dir in target_dir_list:
            dir_suffix = os.path.basename(os.path.normpath(target_dir))
            log_path_base = f"request_params/item_type_mapping/result/verify_schema_usage_{role}_{dir_suffix}.log"
            log_path = get_unique_log_path(log_path_base)
            mapping_types = ["ddi_mapping", "lom_mapping", "jpcoar_v1_mapping", "jpcoar_mapping", "oai_dc_mapping"]

            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)


            summary = {}
            total_unused = 0
            details = []

            for mapping_type in mapping_types:
                schema_mt = mapping_type_schemas.get(mapping_type)
                if not schema_mt:
                    details.append(f"[ERROR] schema not found for: {mapping_type}\n")
                    summary[mapping_type] = (0, 0)
                    continue
                schema_leaves = find_attribute_leaves(schema_mt)
                usage = collect_used_leaves_detailed(target_dir, mapping_type, schema_leaves)

                used_count = 0
                total_count = 0
                unused_count = 0

                # リーフノードごとに@value/@attributesをカウント
                for leaf, attr_names in schema_leaves:
                    total_count += 1  # @value
                    if usage[leaf]["@value"]:
                        used_count += 1
                    else:
                        unused_count += 1
                    for attr in attr_names:
                        total_count += 1
                        if usage[leaf]["@attributes"][attr]:
                            used_count += 1
                        else:
                            unused_count += 1

                summary[mapping_type] = (used_count, total_count)
                total_unused += unused_count

                # 詳細ログ(successディレクトリは未使用ファイルを表示)
                if "success" in target_dir:
                    append_usage_details(details, mapping_type, schema_leaves, usage, title="未使用ファイル", only_unused=True)
                elif "success" not in target_dir:
                    append_usage_details(details, mapping_type, schema_leaves, usage)

                # 詳細ログ（全表示、 対象テストファイルが多い場合は注意）
                # append_usage_details(details, mapping_type, schema_leaves, usage)

            # ログファイル出力
            with open(log_path, "w", encoding="utf-8") as log:
                # サマリーログ
                log.write("=== 検証結果 ===\n")
                log.write("調査対象ディレクトリ: {}\n".format(target_dir))
                for mapping_type in mapping_types:
                    used, total = summary.get(mapping_type, (0, 0))
                    log.write(f"{mapping_type}: {used}/{total}\n")
                log.write(f"未使用: {total_unused}\n\n")
                for line in details:
                    log.write(line)
    print("検証結果を request_params/item_type_mapping/result に出力しました。")

if __name__ == "__main__":
    main()