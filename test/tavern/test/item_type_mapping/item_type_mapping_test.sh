#!/bin/bash

start_time=$(date +%s)

# config.yamlから各設定値を取得
CONFIG_PATH="test/tavern/test/config.yaml"

host=$(grep '^  host:' "$CONFIG_PATH" | awk '{print $2}')
item_type_id=$(grep '^    item_type_id:' "$CONFIG_PATH" | awk '{print $2}')
metadata_id1=$(grep '^    metadata_id1:' "$CONFIG_PATH" | awk '{print $2}')
metadata_id2=$(grep '^    metadata_id2:' "$CONFIG_PATH" | awk '{print $2}')
test_file1=$(grep '^    test_file1:' "$CONFIG_PATH" | awk '{print $2}')
test_file2=$(grep '^    test_file2:' "$CONFIG_PATH" | awk '{print $2}')
sleep_wait=$(grep '^    sleep_wait:' "$CONFIG_PATH" | awk '{print $2}')
max_count=$(grep '^    max_count:' "$CONFIG_PATH" | awk '{print $2}')

# テストモード判定（例: select or all　デフォルト：all）
option_cmd=${1:-all}
shift

pytest_opts=""
use_marker=0

pytest_opts="$pytest_opts -v"
TARGET_TEST_PATH="test/tavern/test/item_type_mapping/target_test.txt"
if [ "$option_cmd" = "select" ]; then
  if [ ! -f "$TARGET_TEST_PATH" ] || [ ! -s "$TARGET_TEST_PATH" ]; then
    echo "エラー: $TARGET_TEST_PATH が存在しないか空です。"
    exit 1
  fi
  # 対象テストを取得
  target_test=$(grep -v '^\s*#' "$TARGET_TEST_PATH" | grep -v '^\s*$' | head -n 1)
  if [ -z "$target_test" ]; then
    echo "エラー: $TARGET_TEST_PATH に有効なテスト指定がありません。"
    exit 1
  fi
  pytest_opts="$pytest_opts -m \"$target_test\""
fi

loop_count=${1:-1}

# (1)テストデータ生成
cd test/tavern
docker compose exec tavern python generator/json/generate_request_body.py "$item_type_id" "$metadata_id1" "$metadata_id2" "$loop_count"

# (2)テスト実行
eval docker compose exec tavern pytest $pytest_opts /tavern/test/"$test_file1"


if [ "$option_cmd" = "all" ] || [[ "$target_test" == *duplicate_check* ]]; then
  # (3)設定値をTrueに変更
  sed -i 's/DISABLE_DUPLICATION_CHECK = False/DISABLE_DUPLICATION_CHECK = True/' ../../modules/weko-itemtypes-ui/weko_itemtypes_ui/config.py
  echo "設定値を変更しました: DISABLE_DUPLICATION_CHECK = True"
  cd ../../
  docker-compose restart web

  # webが200を返すまで待機、指定回数まで200が返らなければ終了
  count=0
  until curl -sk -o /dev/null -w "%{http_code}" "$host" | grep -q "200"; do
    echo "再起動待機中..."
    sleep "$sleep_wait"
    count=$((count + 1))
    if [ "$count" -ge "$max_count" ]; then
      echo "再起動に失敗しました。処理を終了します。"
      exit 1
    fi
  done

  # (4)設定値変更後の二度目のテスト実行
  cd test/tavern
  eval docker compose exec tavern pytest $pytest_opts /tavern/test/"$test_file2"
fi

# (5)スキーマを全て使用しているか確認
docker compose exec tavern python helper/verify_schema_usage.py

# (6)test_dataディレクトリをzip化
cd request_params/item_type_mapping/
zip -rq test_data_$(date +%Y%m%d_%H%M%S).zip test_data
echo "test_dataディレクトリをzip化し、 request_params/item_type_mapping に出力しました。"

# (7)test_dataディレクトリを空にする
rm -rf test_data/*

# (8)設定値をFalseに変更
if [ "$option_cmd" = "all" ] || [[ "$target_test" == *duplicate_check* ]]; then
  cd ../../../../
  sed -i 's/DISABLE_DUPLICATION_CHECK = True/DISABLE_DUPLICATION_CHECK = False/' modules/weko-itemtypes-ui/weko_itemtypes_ui/config.py
  echo "設定値を変更しました: DISABLE_DUPLICATION_CHECK = False"
  docker-compose restart web
fi

echo "処理が終了しました。"

end_time=$(date +%s)
elapsed=$((end_time - start_time))
echo "所要時間: $((elapsed / 60))分 $((elapsed % 60))秒"
  