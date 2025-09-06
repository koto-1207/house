# events.py
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlite_db_presence import db, User, Event

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")


def jst_to_utc_naive(date_str: str, time_str: str) -> datetime:
    """'YYYY-MM-DD' + 'HH:MM'（JST入力）を UTC naive datetime に変換"""
    jst_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00").replace(tzinfo=JST)
    return jst_dt.astimezone(UTC).replace(tzinfo=None)


def _initials_for_edit(ev) -> tuple[str, str, str]:
    """Event(UTC naive)から JST の initial_date/time を作る"""
    s = ev.start_at.replace(tzinfo=UTC).astimezone(JST)
    e = ev.end_at.replace(tzinfo=UTC).astimezone(JST)
    return s.strftime("%Y-%m-%d"), s.strftime("%H:%M"), e.strftime("%H:%M")


def _ev_pk(ev):
    """Eventインスタンスの主キー値を返す（公開APIのみ使用）"""
    return ev.get_id()


def _event_pk_value(ev) -> str:
    """インスタンスから主キー値を取り出す"""
    return ev.get_id()


def build_event_create_modal_view() -> dict:
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
                "block_id": "location_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "場所（任意）"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "event_location",
                    "placeholder": {"type": "plain_text", "text": "例）リビング / Zoom"},
                },
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


def build_event_edit_modal_view(ev) -> dict:
    date_init, start_init, end_init = _initials_for_edit(ev)
    return {
        "type": "modal",
        "callback_id": "event_edit_modal",
        "private_metadata": str(_ev_pk(ev)),
        "title": {"type": "plain_text", "text": "予定を編集"},
        "submit": {"type": "plain_text", "text": "保存"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title_block",
                "label": {"type": "plain_text", "text": "タイトル"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "event_title",
                    "initial_value": ev.title,
                },
            },
            {
                "type": "input",
                "block_id": "date_block",
                "label": {"type": "plain_text", "text": "日付（JST）"},
                "element": {"type": "datepicker", "action_id": "event_date", "initial_date": date_init},
            },
            {
                "type": "input",
                "block_id": "start_block",
                "label": {"type": "plain_text", "text": "開始時刻（JST）"},
                "element": {"type": "timepicker", "action_id": "start_time", "initial_time": start_init},
            },
            {
                "type": "input",
                "block_id": "end_block",
                "label": {"type": "plain_text", "text": "終了時刻（JST）"},
                "element": {"type": "timepicker", "action_id": "end_time", "initial_time": end_init},
            },
            {
                "type": "input",
                "block_id": "location_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "場所（任意）"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "event_location",
                    "initial_value": (ev.location or ""),
                },
            },
            {
                "type": "input",
                "block_id": "memo_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "メモ（任意）"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "event_memo",
                    "multiline": True,
                    "initial_value": (ev.memo or ""),
                },
            },
        ],
    }


def register_events(app):

    @app.action("open_event_create")
    def open_event_create(ack, body, client, logger):
        ack()
        client.views_open(trigger_id=body["trigger_id"], view=build_event_create_modal_view())

    @app.view("event_create_modal")
    def handle_event_create(ack, body, client, logger):
        from ui_builders import build_home_blocks

        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]

        title = state["title_block"]["event_title"]["value"]
        date_str = state["date_block"]["event_date"]["selected_date"]
        start_str = state["start_block"]["start_time"]["selected_time"]
        end_str = state["end_block"]["end_time"]["selected_time"]
        location = state.get("location_block", {}).get("event_location", {}).get("value")
        memo = state.get("memo_block", {}).get("event_memo", {}).get("value")

        errors = {}
        if not title or not title.strip():
            errors["title_block"] = "タイトルは必須です。"
        elif len(title) > 30:
            errors["title_block"] = "タイトルは30文字以内にしてください。"

        try:
            start_utc = jst_to_utc_naive(date_str, start_str)
            end_utc = jst_to_utc_naive(date_str, end_str)
            if end_utc <= start_utc:
                errors["end_block"] = "終了は開始より後にしてください。"
        except Exception:
            errors.setdefault("date_block", "日付を選択してください。")
            errors.setdefault("start_block", "開始時刻を選択してください。")
            errors.setdefault("end_block", "終了時刻を選択してください。")

        if location and len(location) > 40:
            errors["location_block"] = "場所は40文字以内にしてください。"
        if memo and len(memo) > 200:
            errors["memo_block"] = "メモは200文字以内にしてください。"

        if errors:
            ack(response_action="errors", errors=errors)
            return

        ack()
        user_obj, _ = User.get_or_create(slack_user_id=user_id)
        with db.atomic():
            Event.create(
                title=title.strip(),
                start_at=start_utc,
                end_at=end_utc,
                created_by=user_obj,
                location=(location.strip() if location else None),
                memo=(memo.strip() if memo else None),
            )

        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})

    @app.action("event_edit_btn")
    def on_event_edit(ack, body, client, logger):
        ack()
        event_pk = int(body["actions"][0]["value"])
        pk_field = _ev_pk(event_pk)
        ev = Event.get_or_none(pk_field == event_pk)
        if not ev:
            return
        client.views_open(trigger_id=body["trigger_id"], view=build_event_edit_modal_view(ev))

    @app.view("event_edit_modal")
    def handle_event_edit(ack, body, client, logger):
        from ui_builders import build_home_blocks

        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]
        event_pk = int(body["view"]["private_metadata"])
        pk_field = _ev_pk(event_pk)

        title = state["title_block"]["event_title"]["value"]
        date_str = state["date_block"]["event_date"]["selected_date"]
        start_str = state["start_block"]["start_time"]["selected_time"]
        end_str = state["end_block"]["end_time"]["selected_time"]
        location = state.get("location_block", {}).get("event_location", {}).get("value")
        memo = state.get("memo_block", {}).get("event_memo", {}).get("value")

        errors = {}
        if not title or not title.strip():
            errors["title_block"] = "タイトルは必須です。"

        try:
            start_utc = jst_to_utc_naive(date_str, start_str)
            end_utc = jst_to_utc_naive(date_str, end_str)
            if end_utc <= start_utc:
                errors["end_block"] = "終了は開始より後にしてください。"
        except Exception:
            errors.setdefault("date_block", "日付を選択してください。")
            errors.setdefault("start_block", "開始時刻を選択してください。")
            errors.setdefault("end_block", "終了時刻を選択してください。")

        if location and len(location) > 40:
            errors["location_block"] = "場所は40文字以内にしてください。"
        if memo and len(memo) > 200:
            errors["memo_block"] = "メモは200文字以内にしてください。"

        if errors:
            ack(response_action="errors", errors=errors)
            return

        ack()
        with db.atomic():
            (
                Event.update(
                    {
                        Event.title: title.strip(),
                        Event.start_at: start_utc,
                        Event.end_at: end_utc,
                        Event.location: (location.strip() if location else None),
                        Event.memo: (memo.strip() if memo else None),
                    }
                )
                .where(pk_field == event_pk)  # ← 主キーで UPDATE
                .execute()
            )

        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})

    @app.action("event_delete_btn")
    def on_event_delete(ack, body, client, logger):
        from ui_builders import build_home_blocks

        ack()
        user_id = body["user"]["id"]
        event_pk = int(body["actions"][0]["value"])
        pk_field = _ev_pk(event_pk)
        with db.atomic():
            Event.delete().where(pk_field == event_pk).execute()  # ← 主キーで DELETE

        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})
