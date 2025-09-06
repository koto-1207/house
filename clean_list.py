from datetime import datetime
import sqlite3

# 掃除箇所の一覧
CLEAN_LOCATIONS = [
    "キッチン",
    "男子トイレ1階",
    "女子トイレ1階",
    "男子トイレ2階",
    "女子トイレ2階",
    "お風呂（男）",
    "お風呂（女）",
    "脱衣所（男）",
    "脱衣所（女）",
    "広間",
    "廊下1階",
    "廊下2階",
    "階段",
    "玄関",
]

def register_clean_list(app):
    # 「お掃除チェック」ボタンが押されたときの処理
    @app.action("check_cleaning")
    def handle_cleaning_button(ack, body, client):
        ack()
        print("✅ check_cleaning ボタンが押されました！")

        channel_id = body.get("channel", {}).get("id") or body["user"]["id"]

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "どこを掃除しましたか？"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "select_location",
                    "placeholder": {"type": "plain_text", "text": "掃除箇所を選択"},
                    "options": [
                        {"text": {"type": "plain_text", "text": loc}, "value": loc}
                        for loc in CLEAN_LOCATIONS
                    ],
                },
            }
        ]

        client.chat_postMessage(channel=channel_id, blocks=blocks, text="掃除箇所を選んでください")

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
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "note_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "note_input",
                            "multiline": True,
                        },
                        "label": {"type": "plain_text", "text": f"{location} の掃除メモ"},
                    }
                ],
                "private_metadata": f"{user_id}|{location}",
            },
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
            channel=user_id,
            text=f"<@{user_id}> さんが *{location}* を掃除しました！🧼\n📝 メモ: {note}",
        )

    # 履歴表示ボタンが押されたときの処理
    @app.action("view_cleaning_logs")
    def handle_view_logs(ack, body, client):
        ack()
        user_id = body["user"]["id"]
        logs = fetch_recent_cleaning_logs()

        if not logs:
            text = "🧼 掃除記録がまだありません！"
        else:
            text = "*最近の掃除記録🧹*\n"
            for slack_user_id, location, note, timestamp in logs:
                text += f"• <@{slack_user_id}> が *{location}* を掃除（{timestamp}）\n　📝 {note}\n"

        client.chat_postMessage(channel=user_id, text=text)

# 掃除ログをDBに保存
def save_cleaning_log(user_id, location, note):
    conn = sqlite3.connect("shared_house.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cleaning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slack_user_id TEXT,
            location TEXT,
            note TEXT,
            timestamp DATETIME
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO cleaning_logs (slack_user_id, location, note, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, location, note, datetime.now()),
    )
    conn.commit()
    conn.close()

# 掃除ログを取得（最新5件）
def fetch_recent_cleaning_logs(limit=5):
    conn = sqlite3.connect("shared_house.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT slack_user_id, location, note, timestamp
        FROM cleaning_logs
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    logs = cursor.fetchall()
    conn.close()
    return logs
