# clean_list.py
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from peewee import JOIN  # （未使用でも最小変更のため残置）

from sqlite_db_presence import db, User, CleaningLog

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


# ==== 履歴取得（型ゆらぎに強い: Python側でフィルタ） ====
def _fetch_logs(days: int | None, limit: int = 60):
    """
    CleaningLog を新しい順で取得。days=None は全期間。
    ここでは DB の型揺れ対策として、取得後に Python 側で期間フィルタします。
    """
    q = CleaningLog.select().order_by(CleaningLog.timestamp.desc())
    rows = list(q)

    # "7"/"30"/"all" の混在に対応
    _days: int | None = None
    if days is not None:
        try:
            _days = int(days)
        except Exception:
            _days = None

    if _days and _days > 0:
        since_jst_date = datetime.now(TZ_JST).date() - timedelta(days=_days - 1)

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
                dt = datetime.utcnow()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ_UTC)
            return dt.astimezone(TZ_JST)

        rows = [r for r in rows if _to_jst(getattr(r, "timestamp", None)).date() >= since_jst_date]

    return rows[:limit]


def _fmt_log_line(row: CleaningLog) -> str:
    ts = row.timestamp

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
            dt = datetime.utcnow()

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_UTC)
        return dt.astimezone(TZ_JST)

    ts_jst = _to_jst(ts)
    label = ts_jst.strftime("%m/%d %H:%M")
    uid = getattr(row, "user", None)
    uid = getattr(uid, "slack_user_id", "") if uid else ""

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


# === 掃除チェック用のモーダル ===
def _build_cleaning_modal(user_id: str) -> dict:
    """掃除箇所選択 + メモ入力を1枚のモーダルで"""
    return {
        "type": "modal",
        "callback_id": "cleaning_log_modal",
        "title": {"type": "plain_text", "text": "お掃除チェック"},
        "submit": {"type": "plain_text", "text": "記録する"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "private_metadata": user_id,
        "blocks": [
            {
                "type": "input",
                "block_id": "loc_block",
                "label": {"type": "plain_text", "text": "掃除箇所"},
                "element": {
                    "type": "static_select",
                    "action_id": "clean_location",
                    "placeholder": {"type": "plain_text", "text": "選択してください"},
                    "options": [
                        {"text": {"type": "plain_text", "text": loc}, "value": loc} for loc in CLEAN_LOCATIONS
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
                    "action_id": "note_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "気づき・状態など"},
                },
            },
        ],
    }


def register_clean_list(app):
    # CleaningLog テーブルが無い環境でも安全に起動
    try:
        db.create_tables([CleaningLog])
    except Exception:
        pass

    # ====== 掃除チェック：Home ボタン → モーダルを開く ======
    @app.action("cleaning_open")  # Home のボタン action_id
    def handle_cleaning_open(ack, body, client, logger):
        ack()
        user_id = body["user"]["id"]
        client.views_open(trigger_id=body["trigger_id"], view=_build_cleaning_modal(user_id))

    @app.action("check_cleaning")  # 互換: 既存の action_id でも同じ挙動
    def handle_check_cleaning_compat(ack, body, client, logger):
        ack()
        user_id = body["user"]["id"]
        client.views_open(trigger_id=body["trigger_id"], view=_build_cleaning_modal(user_id))

    # ====== 掃除チェック：モーダル送信 ======
    # 置き換え：@app.view("cleaning_log_modal") のハンドラ全体


    @app.view("cleaning_log_modal")
    def handle_cleaning_submit(ack, body, client, logger):
        view = body.get("view", {})  # ★ view 以下に各値があります
        user = body.get("user", {})  # 念のためフォールバック用
        user_id = view.get("private_metadata") or user.get("id")  # ★ 修正
        state = view.get("state", {}).get("values", {})  # ★ 修正

        # 値を取り出し
        loc_sel = state.get("loc_block", {}).get("clean_location", {}).get("selected_option")
        note_val = state.get("note_block", {}).get("note_input", {}).get("value")

        # バリデーション
        errors = {}
        if not loc_sel:
            errors["loc_block"] = "掃除箇所を選択してください。"
        if note_val and len(note_val) > 200:
            errors["note_block"] = "メモは200文字以内にしてください。"

        if errors:
            ack(response_action="errors", errors=errors)
            return

        # 保存して完了画面に更新
        try:
            _save_cleaning_log(user_id, loc_sel["value"], (note_val or "").strip())
        except Exception:
            logger.exception("saving CleaningLog failed")

        ack(
            response_action="update",
            view={
                "type": "modal",
                "callback_id": "cleaning_log_done",
                "title": {"type": "plain_text", "text": "お掃除チェック"},
                "close": {"type": "plain_text", "text": "閉じる"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "✅ 記録しました。ご協力ありがとうございます！"},
                    },
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*場所:* {loc_sel['value']}"}},
                    (
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"*メモ:* {note_val.strip()}"}}
                        if (note_val and note_val.strip())
                        else {"type": "section", "text": {"type": "mrkdwn", "text": "_メモ: （なし）_"}}
                    ),
                ],
            },
        )

    # ====== 掃除履歴（既存のモーダル遷移） ======
    @app.action("cleaning_history")
    def open_history_modal(ack, body, client, logger):
        ack()
        try:
            client.views_open(trigger_id=body["trigger_id"], view=_build_history_modal_empty())
        except Exception as e:
            logger.exception("cleaning_history failed")

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
