import json
import requests
import sys
import os
import hashlib

def print_usage():
    print("Usage:")
    print("  python3 import_task_client.py import <zip_file> [behalf=<string>]")
    print("  python3 import_task_client.py check <zip_file> [behalf=<string>]")
    sys.exit(1)

if len(sys.argv) < 3:
    print_usage()

mode = sys.argv[1]

config_file = 'config.json'
with open(config_file, 'r') as file:
    config = json.load(file)

hostname = config['hostname']
access_token = config['access_token']

if mode in ("import", "check"):
    filename = sys.argv[2]
    on_behalf_of = None
    is_change_identifier = False
    for arg in sys.argv[3:]:
        if arg.startswith("behalf="):
            on_behalf_of = arg.split("=", 1)[1]
        if arg == "change_id":
            is_change_identifier = True

    if not os.path.isfile(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    with open(filename, 'rb') as f:
        file_data = f.read()
        digest = hashlib.sha256(file_data).hexdigest()

    headers = {
        "Content-Disposition": f"attachment; filename={os.path.basename(filename)}",
        "Authorization": f"Bearer {access_token}",
        "Packaging": "http://purl.org/net/sword/3.0/package/SimpleZip",
        "Digest": f"SHA-256={digest}",
    }
    files = {
        "file": (os.path.basename(filename), open(filename, 'rb'), "application/zip"),
    }
    data = {}
    if on_behalf_of:
        data["on_behalf_of"] = on_behalf_of
    if is_change_identifier:
        data["is_change_identifier"] = "true"

    url = f"{hostname}/sword/import-task/{mode}"

    print("リクエストURL:", url)
    print("リクエストヘッダー:", headers)
    response = requests.post(url, headers=headers, files=files, data=data, verify=False)

    if response.status_code in (200, 201, 202):
        print("リクエストが送信されました。")
        try:
            response_data = response.json()
            print("レスポンス:", json.dumps(response_data, ensure_ascii=False, indent=2))
            if mode == "check":
                if response_data.get("can_import"):
                    print("このファイルはインポート可能です。")
                else:
                    print("このファイルはインポートできません。")
            elif mode == "import":
                if response_data.get("can_import"):
                    print("インポートタスクが登録されました。task_id:", response_data.get("task_id"))
                else:
                    print("インポートに失敗しました。")
        except json.JSONDecodeError:
            print("レスポンスの解析に失敗しました。レスポンス内容:", response.text)
    else:
        print("エラーが発生しました:", response.status_code, response.text)
else:
    print_usage()