import json
import requests
import sys
import os

def print_usage():
    print("Usage:")
    print("  python3 import_task_status_client.py <task_id>")
    sys.exit(1)

if len(sys.argv) != 2:
    print_usage()

task_id = sys.argv[1]
config_file = 'config.json'

if not os.path.isfile(config_file):
    print(f"Error: Config file '{config_file}' not found.")
    sys.exit(1)

with open(config_file, 'r') as file:
    config = json.load(file)

hostname = config['hostname']
access_token = config['access_token']

url = f"{hostname}/api/items/import-task/get_bulk_import_task_status/{task_id}"
headers = {
    "Authorization": f"Bearer {access_token}",
}

print("リクエストURL:", url)
print("リクエストヘッダー:", headers)
response = requests.get(url, headers=headers, verify=False)
try:
    response_data = response.json()
    if response.status_code == 200:
            print("インポートタスク状況:", response.status_code, json.dumps(
                response_data, ensure_ascii=False, indent=2))
    else:
        print("エラーが発生しました:", response.status_code, json.dumps(
            response_data, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print("レスポンスの解析に失敗しました。レスポンス内容:",
        response.status_code, json.dumps(
        response_data, ensure_ascii=False, indent=2))
