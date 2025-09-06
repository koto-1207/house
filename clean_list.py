# clean_list.py
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from peewee import JOIN

from sqlite_db_presence import db, User, CleaningLog  # フォールバック

TZ_JST = ZoneInfo("Asia/Tokyo")
TZ_UTC = ZoneInfo("UTC")

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


def _to_utc_naive(dt_jst: datetime) -> datetime:
    if dt_jst.tzinfo is None:
        dt_jst = dt_jst.replace(tzinfo=TZ_JST)
    return dt_jst.astimezone(TZ_UTC).replace(tzinfo=None)


def _ellipsis(s: str | None, n: int = 60) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def _save_cleaning_log(user_id: str, location: str, note: str | None):
    user_obj, _ = User.get_or_create(slack_user_id=user_id)
    with db.atomic():
        CleaningLog.create(user=user_obj, location=location, note=(note or "").strip())


def _fetch_logs(days: int | None, limit: int = 60):
    """
    CleaningLog を新しい順で取得。days=None は全期間。
    DB保存はUTC naiveなので、JST日付での下限はUTCに変換してから検索。
    """
    q = (
        CleaningLog.select(CleaningLog, User)
        .join(User, JOIN.LEFT_OUTER)
        .order_by(CleaningLog.timestamp.desc())
        .limit(limit)
    )
    if days is not None:
        today_jst = datetime.now(TZ_JST).date()
        since_jst = today_jst - timedelta(days=days - 1)
        lower_jst = datetime.combine(since_jst, time(0, 0), tzinfo=TZ_JST)
        lower_utc_naive = _to_utc_naive(lower_jst)
        q = (
        CleaningLog
        .select()
        .order_by(CleaningLog.timestamp.desc())
        .limit(limit)
        )
    return list(q)


def _fmt_log_line(row: CleaningLog) -> str:
    ts = row.timestamp

    # 既存の時刻正規化（前回案と同じ）
    def _to_jst(ts_val):
        if isinstance(ts_val, datetime):
            dt = ts_val
        elif isinstance(ts_val, (str, bytes)):
            s = ts_val.decode("utf-8", "ignore") if isinstance(ts_val, bytes) else ts_val
            s = s.strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s)
            except Exception:
                try:
                    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    dt = datetime.utcnow()
        else:
            try:
                dt = datetime.combine(ts_val, time(0, 0))
            except Exception:
                dt = datetime.utcnow()

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_UTC)
        return dt.astimezone(TZ_JST)

    ts_jst = _to_jst(ts)
    label = ts_jst.strftime("%m/%d %H:%M")
    uid = getattr(row.user, "slack_user_id", "") if row.user else ""

    # ★ ここを修正：note を安全に文字列化してから strip
    def _to_text(v):
        if v is None:
            return ""
        if isinstance(v, bytes):
            return v.decode("utf-8", "ignore")
        return str(v)

    note_text = _to_text(row.note).strip()
    note_part = f" ｜ {_ellipsis(note_text, 40)}" if note_text else ""

    return f"・{label} ｜ {row.location} ｜ <@{uid}>{note_part}"


def _build_history_blocks(days: int | None = 7) -> list[dict]:
    period_label = {7: "過去7日", 30: "過去30日", None: "全期間"}[days]
    rows = _fetch_logs(days=days, limit=60)
    body = "\n".join(_fmt_log_line(r) for r in rows) if rows else "記録がありません。"
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*🗂️ 掃除履歴* — {period_label}"}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "過去7日"},
                    "action_id": "history_days_7",
                    "value": "7",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "過去30日"},
                    "action_id": "history_days_30",
                    "value": "30",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "全期間"},
                    "action_id": "history_days_all",
                    "value": "all",
                },
            ],
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": body}},
    ]


def _build_history_modal(days: int | None = 7) -> dict:
    meta = "all" if days is None else str(days)
    return {
        "type": "modal",
        "callback_id": "cleaning_history_modal",
        "title": {"type": "plain_text", "text": "掃除履歴"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "private_metadata": meta,
        "blocks": _build_history_blocks(days),
    }


def _build_history_modal_empty() -> dict:
    return {
        "type": "modal",
        "callback_id": "cleaning_history_modal",
        "title": {"type": "plain_text", "text": "掃除履歴"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "private_metadata": "init",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*🗂️ 掃除履歴* — 期間を選んでください"}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "過去7日"},
                        "action_id": "history_days_7",
                        "value": "7",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "過去30日"},
                        "action_id": "history_days_30",
                        "value": "30",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "全期間"},
                        "action_id": "history_days_all",
                        "value": "all",
                    },
                ],
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "（まだ期間が選択されていません）"}},
        ],
    }


def register_clean_list(app):
    # ★ 2) CleaningLog テーブルが無い環境でも安全に起動
    try:
        db.create_tables([CleaningLog])
    except Exception:
        pass

    def _post_clean_select(client, channel_id):
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

    # ====== 掃除チェック ======
    @app.action("check_cleaning")
    def handle_cleaning_button(ack, body, client, logger):
        ack()
        # ★ 3) Home から押された場合は DM を開いてから投稿
        user_id = body["user"]["id"]
        channel_id = (body.get("channel") or {}).get("id")
        if not channel_id:
            opened = client.conversations_open(users=user_id)
            channel_id = opened["channel"]["id"]

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

        # @メンションで「掃除」などを含むときも同じUIを出す

    @app.event("app_mention")
    def on_mention_clean(event, client, logger):
        text = event.get("text", "")
        if any(k in text for k in ("掃除チェック")):
            channel_id = event["channel"]
            _post_clean_select(client, channel_id)

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
                "private_metadata": f"{user_id}|{location}",
            },
        )

    @app.view("submit_cleaning_note")
    def handle_note_submission(ack, body, client, logger):
        ack()
        metadata = body["view"]["private_metadata"]
        user_id, location = metadata.split("|", 1)
        note = ""
        try:
            note = body["view"]["state"]["values"]["note_block"]["note_input"]["value"] or ""
        except Exception:
            pass
        _save_cleaning_log(user_id, location, note)
        client.chat_postMessage(
            channel=user_id,
            text=f"<@{user_id}> さんが *{location}* を掃除しました！🧼\n📝 メモ: {note or '（なし）'}",
        )

    # ====== 掃除履歴 ======
    @app.action("cleaning_history")
    def open_history_modal(ack, body, client, logger):
        ack()
        try:
            client.views_open(trigger_id=body["trigger_id"], view=_build_history_modal_empty())
        except Exception as e:
            logger.exception("cleaning_history failed")
            # エラー内容をDMでも通知（Homeからの押下でchannelが無い場合があるため）
            try:
                ch = client.conversations_open(users=body["user"]["id"])["channel"]["id"]
                client.chat_postMessage(channel=ch, text=f"履歴モーダルでエラー: {e}")
            except Exception:
                pass

    @app.action("history_days_7")
    @app.action("history_days_30")
    @app.action("history_days_all")
    def change_history_range(ack, body, client, logger):
        ack()
        val = body["actions"][0]["value"]  # "7" / "30" / "all"
        days = None if val == "all" else int(val)
        client.views_update(
            view_id=body["view"]["id"],
            hash=body["view"]["hash"],
            view=_build_history_modal(days=days),
        )
