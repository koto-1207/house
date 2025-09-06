# clean_list.py
# 掃除記録機能（SlackBot）
# 「お掃除チェック」ボタン → 掃除箇所選択 → メモ入力 → DB保存 → Slack通知

from datetime import datetime
from zoneinfo import ZoneInfo
import os
import sqlite3

TZ_JST = ZoneInfo("Asia/Tokyo")

# 既存のDBと分裂しないように同じパスを使う（環境変数 DB_PATH があればそれを使う）
DB_PATH = os.getenv("DB_PATH", "house.db")

CLEAN_LOCATIONS = [
    "キッチン",
    "トイレ1階男",
    "トイレ1階女",
    "トイレ2階男",
    "トイレ2階女",
    "お風呂男",
    "お風呂女",
    "脱衣所男",
    "脱衣所女",
    "広間",
    "廊下1階",
    "廊下2階",
    "階段",
    "玄関",
]


def _ensure_table():
    """cleaning_logs テーブルを作成（存在すれば何もしない）"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cleaning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slack_user_id TEXT NOT NULL,
                location TEXT NOT NULL,
                note TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _save_cleaning_log(user_id: str, location: str, note: str | None):
    """掃除ログを保存"""
    ts = datetime.now(TZ_JST).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cleaning_logs (slack_user_id, location, note, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, location, note or "", ts),
        )
        conn.commit()
    finally:
        conn.close()


def register_clean_list(app):
    """掃除機能のイベント/アクションを登録"""

    _ensure_table()

    # Home の「🧹 掃除チェック」ボタン
    @app.action("check_cleaning")
    def handle_cleaning_button(ack, body, client, logger):
        ack()
        logger.info("check_cleaning ボタン押下")

        # Homeボタンからの押下では body["channel"] が無いことがある → DM にフォールバック
        channel_id = (body.get("channel") or {}).get("id") or body["user"]["id"]

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "どこを掃除しましたか？"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "select_location",
                    "placeholder": {"type": "plain_text", "text": "掃除箇所を選択"},
                    "options": [
                        {"text": {"type": "plain_text", "text": loc}, "value": loc} for loc in CLEAN_LOCATIONS
                    ],
                },
            }
        ]

        client.chat_postMessage(channel=channel_id, blocks=blocks, text="掃除箇所を選んでください")

    # 掃除箇所の選択 → メモ入力モーダル
    @app.action("select_location")
    def handle_location_selection(ack, body, client, logger):
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
                "close": {"type": "plain_text", "text": "やめる"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "note_block",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "note_input",
                            "multiline": True,
                            "placeholder": {"type": "plain_text", "text": "気づき・状態など（任意）"},
                        },
                        "label": {"type": "plain_text", "text": f"{location} の掃除メモ"},
                    }
                ],
                # user_id と location を private_metadata で運ぶ
                "private_metadata": f"{user_id}|{location}",
            },
        )

    # モーダル送信 → DB保存 → DM通知
    @app.view("submit_cleaning_note")
    def handle_note_submission(ack, body, client, logger):
        ack()
        metadata = body["view"]["private_metadata"]
        user_id, location = metadata.split("|", 1)

        note = ""
        try:
            note = body["view"]["state"]["values"]["note_block"]["note_input"]["value"] or ""
        except Exception:
            note = ""

        _save_cleaning_log(user_id, location, note)

        client.chat_postMessage(
            channel=user_id,
            text=f"<@{user_id}> さんが *{location}* を掃除しました！🧼\n📝 メモ: {note or '（なし）'}",
        )
