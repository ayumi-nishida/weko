import json
import requests
import sys
import os
import hashlib

def print_usage():
    print("Usage:")
    print("  python3 import_task_client.py <mode=import|check> "
          "<zip_file> [is_change_identifier=True|False] [behalf=<string>]")
    sys.exit(1)

if len(sys.argv) < 2:
    print_usage()

mode = "import"
is_change_identifier = False
filename = None
on_behalf_of = None

for arg in sys.argv[1:]:
    if arg.startswith("mode="):
        mode = arg.split("=", 1)[1]
    elif arg.startswith("is_change_identifier="):
        is_change_identifier = arg.split("=", 1)[1].lower()
    elif arg.endswith(".zip"):
        filename = arg
    elif arg.startswith("behalf="):
        on_behalf_of = arg.split("=", 1)[1]

config_file = 'config.json'
with open(config_file, 'r') as file:
    config = json.load(file)

hostname = config['hostname']
access_token = config['access_token']

if mode in ("import", "check") and filename is not None:
    if not os.path.isfile(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    with open(filename, 'rb') as f:
        file_data = f.read()
        digest = hashlib.sha256(file_data).hexdigest()

    headers = {
        "Content-Disposition":
            f"attachment; filename={os.path.basename(filename)}",
        "Authorization": f"Bearer {access_token}",
        "Packaging": "http://purl.org/net/sword/3.0/package/SimpleZip",
        "Digest": f"SHA-256={digest}",
    }
    files = {
        "file": (os.path.basename(filename), open(filename, 'rb'),
                 "application/zip"),
    }

    if on_behalf_of:
        headers["On-Behalf-Of"] = on_behalf_of

    # クエリパラメータを動的に構築
    url = f"{hostname}/api/items/import-task?mode={mode}&is_change_identifier={is_change_identifier}"

    print("リクエストURL:", url)
    print("リクエストヘッダー:", headers)
    response = requests.post(url, headers=headers,
                             files=files, verify=False)
    try:
        response_data = response.json()
        if response.status_code in (200, 201, 202):
            print("リクエストが送信されました。")
            print("レスポンス:", response.status_code, json.dumps(response_data,
                                    ensure_ascii=False, indent=2))
            if mode == "check":
                if response_data.get("can_import"):
                    print("このファイルはインポート可能です。")
                else:
                    print("このファイルはインポートできません。")
            elif mode == "import":
                if response_data.get("can_import"):
                    print("インポートタスクが登録されました。task_id:",
                        response_data.get("task_id"))
                else:
                    print("インポートに失敗しました。")
        else:
            print("エラーが発生しました:", response.status_code, json.dumps(
                response_data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print("レスポンスの解析に失敗しました。レスポンス内容:",
            response.status_code, json.dumps(
            response_data, ensure_ascii=False, indent=2)
            )
else:
    print_usage()
