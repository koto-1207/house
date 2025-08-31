# presence.py
from datetime import datetime
from zoneinfo import ZoneInfo
from slack_sdk.errors import SlackApiError  # ← 任意（ログ用）
from splite_db_presence import db, User, PresenceLog
from ui_builders import build_home_blocks


def register_presence(app):
    @app.action("open_presence")
    def open_presence(ack, body, client, logger):
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "presence_modal",
                "title": {"type": "plain_text", "text": "在宅状況の更新"},
                "submit": {"type": "plain_text", "text": "保存"},
                "close": {"type": "plain_text", "text": "閉じる"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "status_block",
                        "label": {"type": "plain_text", "text": "今日のステータス"},
                        "element": {
                            "type": "radio_buttons",
                            "action_id": "presence_status",
                            "options": [
                                {"text": {"type": "plain_text", "text": "在宅"}, "value": "home"},
                                {"text": {"type": "plain_text", "text": "外出"}, "value": "away"},
                            ],
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "note_block",
                        "optional": True,
                        "label": {"type": "plain_text", "text": "メモ（任意）"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "presence_note",
                            "multiline": True,
                        },
                    },
                ],
            },
        )

    @app.view("presence_modal")
    def handle_presence_submission(ack, body, client, logger):
        # ① ACK（必須）
        ack()

        # ② 入力値
        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]
        status = state["status_block"]["presence_status"]["selected_option"]["value"]
        note = state.get("note_block", {}).get("presence_note", {}).get("value")

        # ③ ユーザー確保
        user_obj, _ = User.get_or_create(slack_user_id=user_id)

        # ④ 日付（JST）と現在時刻（UTC）
        today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        now_utc = datetime.utcnow()

        # ⑤ UPSERT
        with db.atomic():
            (
                PresenceLog.insert(
                    user=user_obj,  # ← インスタンスを渡すと安全
                    date=today_jst,
                    status=status,
                    note=note,
                    updated_at=now_utc,
                )
                .on_conflict(
                    conflict_target=[PresenceLog.user, PresenceLog.date],
                    update={
                        PresenceLog.status: status,
                        PresenceLog.note: note,
                        PresenceLog.updated_at: now_utc,
                    },
                )
                .execute()
            )

        # ⑥ 成功通知（関数の中に！）
        try:
            im = client.conversations_open(users=user_id)  # im:write が必要
            channel_id = im["channel"]["id"]
        except SlackApiError as e:
            logger.error(f"[presence] conversations_open error: {e.response.get('error')}")
            channel_id = user_id  # フォールバック（SlackbotのDMに出る）

        client.chat_postMessage(
            channel=channel_id, text=f"在宅状況を更新しました：{'在宅' if status=='home' else '外出'}"
        )

        client.views_publish(
            user_id=user_id, view={
                "type": "home", "blocks": build_home_blocks(client)
                }
            )
