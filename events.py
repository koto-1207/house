from datetime import datetime
from zoneinfo import ZoneInfo
from splite_db_presence import db, User, Event
from ui_builders import build_home_blocks

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")


def to_utc_naive(date_str: str, time_str: str) -> datetime:
    # "2025-09-01" + "19:00" -> UTCのnaive datetime
    jst_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00").replace(tzinfo=JST)
    return jst_dt.astimezone(UTC).replace(tzinfo=None)


def build_event_create_modal_view() -> dict:
    # ← いま書いてある view={...} の“中身”を丸ごと return に移す
    return {
        "type": "modal",
        "callback_id": "event_create_modal",
        "title": {"type": "plain_text", "text": "予定を追加"},
        "submit": {"type": "plain_text", "text": "作成"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "label": {"type": "plain_text", "text": "タイトル"},
                "element": {"type": "plain_text_input", "action_id": "event_title"},
            },
            {
                "type": "input",
                "block_id": "date_block",
                "label": {"type": "plain_text", "text": "日付（JST）"},
                "element": {"type": "datepicker", "action_id": "event_date"},
            },
            {
                "type": "input",
                "block_id": "start_block",
                "label": {"type": "plain_text", "text": "開始時刻（JST）"},
                "element": {"type": "timepicker", "action_id": "start_time"},
            },
            {
                "type": "input",
                "block_id": "end_block",
                "label": {"type": "plain_text", "text": "終了時刻（JST）"},
                "element": {"type": "timepicker", "action_id": "end_time"},
            },
            {
                "type": "input",
                "block_id": "memo_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "メモ（任意）"},
                "element": {"type": "plain_text_input", "action_id": "event_memo", "multiline": True},
            },
        ],
    }


def register_events(app):
    @app.action("open_event_create")
    def open_event_create(ack, body, client, logger):
        ack()
        trigger_id = body.get("trigger_id")
        if not trigger_id:
            logger.error("[open_event_create] trigger_id missing")
            return
        client.views_open(
            trigger_id=body["trigger_id"],
            view=build_event_create_modal_view(),
        )
    @app.view("event_create_modal")
    def handle_event_create(ack, body, client, logger):
        ack()
        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]
        # 2) 値を取り出す（block_id / action_id はあなたのモーダルに合わせる）
        title = state["title_block"]["event_title"]["value"]
        date_str = state["date_block"]["event_date"]["selected_date"]     # "YYYY-MM-DD"
        start_str = state["start_block"]["start_time"]["selected_time"]   # "HH:MM"
        end_str = state["end_block"]["end_time"]["selected_time"]         # "HH:MM"
        memo = state.get("memo_block", {}).get("event_memo", {}).get("value")
        # 3) バリデーション（終了 > 開始）
        start_utc = to_utc_naive(date_str, start_str)   # 既存の helper を使う
        end_utc = to_utc_naive(date_str, end_str)
        if end_utc <= start_utc:
            ack(  # ← ここで差し戻すときは ack を「上書き」で再送可
                response_action="errors",
                errors={"end_block": "終了は開始より後にしてください。"}
            )
            return
        # 4) ユーザーを確保（FK用）
        user_obj, _ = User.get_or_create(slack_user_id=user_id)
        # 5) INSERT（Peewee）
        with db.atomic():
            Event.create(
                title=title,
                start_at=start_utc,   # UTC naive で保存（方針どおり）
                end_at=end_utc,
                created_by=user_obj,  # FK はインスタンス渡しが安全
                memo=memo
            )
        # 6) Home を再描画（ここが肝：home.py を汚さない）
        client.views_publish(
            user_id=user_id,
            view={"type": "home", "blocks": build_home_blocks(client)}
        )
