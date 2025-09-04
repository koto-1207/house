# 掃除記録機能（SlackBot）
# 「お掃除チェック」ボタン → 掃除箇所選択 → メモ入力 → DB保存 → Slack通知 の流れを管理します。
# CLEAN_LOCATIONS に掃除箇所の一覧を定義しています。

from datetime import datetime
import sqlite3

CLEAN_LOCATIONS = [
    "キッチン", "トイレ1階男", "トイレ1階女", "トイレ2階男", "トイレ2階女",
    "お風呂男", "お風呂女", "脱衣所男", "脱衣所女",
    "広間", "廊下1階", "廊下2階", "階段", "玄関"
]

def register_clean_list(app):
    # 「お掃除チェック」ボタンが押されたときの処理
    @app.action("check_cleaning")
    def handle_cleaning_button(ack, body, client, logger):
        ack()
        logger.info("check_cleaning ボタンが押されました")
        blocks = [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "どこを掃除しましたか？"},
            "accessory": {
                "type": "static_select",
                "action_id": "select_location",
                "placeholder": {"type": "plain_text", "text": "掃除箇所を選択"},
                "options": [
                    {
                        "text": {"type": "plain_text", "text": loc},
                        "value": loc
                    } for loc in CLEAN_LOCATIONS
                ]
            }
        }]
        client.chat_postMessage(
            channel=body["user"]["id"],  # DMに送る
            blocks=blocks,
            text="掃除箇所を選んでください"
        )

    # 掃除箇所が選択されたときの処理
    @app.action("select_location")
    def handle_location_selection(ack, body, client):
        ack()
        location = body["actions"][0]["selected_option"]["value"]
        user_id = body["user"]["id"]

        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "submit_cleaning_note",
                "title": {"type": "plain_text", "text": "掃除メモ"},
                "submit": {"type": "plain_text", "text": "記録する"},
                "blocks": [{
                    "type": "input",
                    "block_id": "note_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "note_input",
                        "multiline": True
                    },
                    "label": {"type": "plain_text", "text": f"{location} の掃除メモ"}
                }],
                "private_metadata": f"{user_id}|{location}"
            }
        )

    # モーダル送信後の処理
    @app.view("submit_cleaning_note")
    def handle_note_submission(ack, body, client):
        ack()
        metadata = body["view"]["private_metadata"]
        user_id, location = metadata.split("|")
        note = body["view"]["state"]["values"]["note_block"]["note_input"]["value"]

        save_cleaning_log(user_id, location, note)

        client.chat_postMessage(
            channel=body["user"]["id"],
            text=f"<@{user_id}> さんが *{location}* を掃除しました！🧼\n📝 メモ: {note}"
        )

    # 掃除ログをDBに保存
    def save_cleaning_log(user_id, location, note):
        conn = sqlite3.connect("shared_house.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cleaning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slack_user_id TEXT,
                location TEXT,
                note TEXT,
                timestamp DATETIME
            )
        """)
        cursor.execute("""
            INSERT INTO cleaning_logs (slack_user_id, location, note, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, location, note, datetime.now()))
        conn.commit()
        conn.close()
