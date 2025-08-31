from datetime import datetime
from zoneinfo import ZoneInfo
from splite_db_presence import db, User, Event
from ui_builders import build_home_blocks

JST = ZoneInfo("Asia/Tokyo")
UTC = ZoneInfo("UTC")


def _initials_for_edit(ev) -> tuple[str, str, str]:
    # UTC naive → JST
    from zoneinfo import ZoneInfo

    s_jst = ev.start_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Tokyo"))
    e_jst = ev.end_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Tokyo"))
    return s_jst.strftime("%Y-%m-%d"), s_jst.strftime("%H:%M"), e_jst.strftime("%H:%M")


def to_utc_naive(date_str: str, time_str: str) -> datetime:
    """'YYYY-MM-DD' + 'HH:MM'（JST入力）を UTC naive datetime に変換"""
    JST = ZoneInfo("Asia/Tokyo")
    UTC = ZoneInfo("UTC")
    jst_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00").replace(tzinfo=JST)
    return jst_dt.astimezone(UTC).replace(tzinfo=None)


def _initials_for_edit(ev) -> tuple[str, str, str]:
    """Event(UTC naive)から JST の initial_date/time を作る"""
    JST = ZoneInfo("Asia/Tokyo")
    UTC = ZoneInfo("UTC")
    s = ev.start_at.replace(tzinfo=UTC).astimezone(JST)
    e = ev.end_at.replace(tzinfo=UTC).astimezone(JST)
    return s.strftime("%Y-%m-%d"), s.strftime("%H:%M"), e.strftime("%H:%M")


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
        "private_metadata": str(ev.id),  # ★ event_id を運ぶ
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
        ack()  # ★ 先にACK（必須）
        client.views_open(
            trigger_id=body["trigger_id"],
            view=build_event_create_modal_view(),  # ★ () を忘れない
        )

    # 予定作成モーダルの送信
    @app.view("event_create_modal")
    def handle_event_create(ack, body, client, logger):
        from ui_builders import build_home_blocks  # ローカルimportで循環回避

        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]

        title = state["title_block"]["event_title"]["value"]
        date_str = state["date_block"]["event_date"]["selected_date"]
        start_str = state["start_block"]["start_time"]["selected_time"]
        end_str = state["end_block"]["end_time"]["selected_time"]
        location = state.get("location_block", {}).get("event_location", {}).get("value")
        memo = state.get("memo_block", {}).get("event_memo", {}).get("value")

        # バリデーション（ackはこの時点ではまだ呼ばない）
        errors = {}
        if not title or not title.strip():
            errors["title_block"] = "タイトルは必須です。"
        elif len(title) > 30:
            errors["title_block"] = "タイトルは30文字以内にしてください。"

        try:
            start_utc = to_utc_naive(date_str, start_str)
            end_utc = to_utc_naive(date_str, end_str)
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

        # 成功ACK → 保存
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

        # Home再描画
        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})

    # 編集ボタン → 編集モーダルを開く
    @app.action("event_edit_btn")
    def on_event_edit(ack, body, client, logger):
        ack()  # ★ 先にACK
        event_id = int(body["actions"][0]["value"])
        ev = Event.get_or_none(Event.id == event_id)
        if not ev:
            return
        client.views_open(
            trigger_id=body["trigger_id"],
            view=build_event_edit_modal_view(ev),  # ★ ev をここで渡す（グローバルで参照しない）
        )

    # 編集モーダルの送信 → UPDATE
    @app.view("event_edit_modal")
    def handle_event_edit(ack, body, client, logger):
        from ui_builders import build_home_blocks

        user_id = body["user"]["id"]
        state = body["view"]["state"]["values"]
        event_id = int(body["view"]["private_metadata"])  # ★ 受け取り

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
            start_utc = to_utc_naive(date_str, start_str)
            end_utc = to_utc_naive(date_str, end_str)
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

        # 成功ACK → UPDATE
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
                .where(Event.id == event_id)
                .execute()
            )

        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})

    # 削除ボタン → DELETE
    @app.action("event_delete_btn")
    def on_event_delete(ack, body, client, logger):
        from ui_builders import build_home_blocks

        ack()  # ★ 先にACK
        user_id = body["user"]["id"]
        event_id = int(body["actions"][0]["value"])
        with db.atomic():
            Event.delete().where(Event.id == event_id).execute()

        client.views_publish(user_id=user_id, view={"type": "home", "blocks": build_home_blocks(client)})
