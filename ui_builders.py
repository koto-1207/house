# ui_builders.py
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from peewee import JOIN

from sqlite_db_presence import User, PresenceLog, Event

# ===== 定数 =====
TZ_JST = ZoneInfo("Asia/Tokyo")
TZ_UTC = ZoneInfo("UTC")


def _event_pk_value(ev):
    return ev.get_id()


def _to_utc_naive(dt_jst: datetime) -> datetime:
    """JSTのaware datetimeをUTC naive（tzinfo=None）に変換"""
    if dt_jst.tzinfo is None:
        dt_jst = dt_jst.replace(tzinfo=TZ_JST)
    return dt_jst.astimezone(TZ_UTC).replace(tzinfo=None)


def _utc_naive_to_jst(dt_utc_naive: datetime) -> datetime:
    """UTC naive（tzinfo=None）をJST awareに変換"""
    return dt_utc_naive.replace(tzinfo=TZ_UTC).astimezone(TZ_JST)


AID_OPEN_MANUALS = "open_manuals"
AID_OPEN_PRESENCE = "open_presence"
AID_OPEN_EVENT_CREATE = "open_event_create"

AID_MANUALS_OPEN = "manuals_open"
AID_CLEANING_OPEN = "cleaning_open"
AID_CLEANING_HISTORY = "cleaning_history"


def _ellipsis(s: str | None, limit: int = 30) -> str:
    if not s:
        return ""
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _weekday_jp(d) -> str:
    return "月火水木金土日"[d.weekday()]


def _fmt_range_from_utc_naive(start_utc_naive, end_utc_naive) -> tuple[str, str, date]:
    s_jst = _utc_naive_to_jst(start_utc_naive)
    e_jst = _utc_naive_to_jst(end_utc_naive)
    return s_jst.strftime("%H:%M"), e_jst.strftime("%H:%M"), s_jst.date()


# Presence（今日の在宅）
def _fetch_today_presence_rows(today_jst) -> list[PresenceLog]:
    """
    今日分の presence_logs を取得。
    PresenceLog.user は User への FK（to_field=slack_user_id）想定。
    """
    rows = (
        PresenceLog.select(PresenceLog, User)
        .join(User, JOIN.LEFT_OUTER)
        .where(PresenceLog.date == today_jst)
        .order_by(PresenceLog.updated_at.desc())
    )
    return list(rows)


def _format_presence_text(rows: list[PresenceLog]) -> str:
    if not rows:
        return "・まだ登録がありません"

    label = {"home": "在宅🏠", "away": "外出🚶"}
    # 最新の入力を優先（同一ユーザーの重複を抑止）
    latest_by_user = {}
    for r in rows:
        uid = getattr(r.user, "slack_user_id", None) or r.user
        if uid not in latest_by_user:
            latest_by_user[uid] = r

    def sort_key(item):
        uid, r = item
        status_order = 0 if r.status == "home" else 1
        return (status_order, uid)

    lines = []
    for uid, r in sorted(latest_by_user.items(), key=sort_key):
        line = f"・<@{uid}> — {label.get(r.status, r.status)}"
        if r.note:
            line += f"｜{_ellipsis(r.note, 40)}"
        lines.append(line)

    return "\n".join(lines)


# Events（今週の予定）
def _fetch_week_event_rows(week_start_jst, week_end_jst) -> list[Event]:
    # JST の [week_start 00:00, week_end+1 00:00)
    lower_jst = datetime.combine(week_start_jst, time(0, 0), tzinfo=TZ_JST)
    upper_jst = datetime.combine(week_end_jst + timedelta(days=1), time(0, 0), tzinfo=TZ_JST)

    lower_utc_naive = _to_utc_naive(lower_jst)
    upper_utc_naive = _to_utc_naive(upper_jst)

    rows = (
        Event.select(Event, User)
        .join(User, JOIN.LEFT_OUTER)
        # ここだけ変更（AND 条件 → between に）
        .where(
            Event.start_at.between(
                lower_utc_naive, upper_utc_naive - timedelta(microseconds=1)  # [lower, upper)
            )
        )
        .order_by(Event.start_at)
    )
    return list(rows)


def _format_events_text(rows: list[Event]) -> str:
    if not rows:
        return "・今週の予定はありません"

    by_day: dict[str, list[str]] = {}
    for ev in rows:
        # 時刻・日付（JST）を整形
        s_hm, e_hm, date_jst = _fmt_range_from_utc_naive(ev.start_at, ev.end_at)
        day_label = f"{date_jst:%m/%d}（{_weekday_jp(date_jst)}）"

        title = _ellipsis(getattr(ev, "title", ""), 30)
        memo = getattr(ev, "memo", None)
        loc = getattr(ev, "location", None)
        memo_part = f" ｜ {_ellipsis(memo, 24)}" if memo else ""
        loc_part = f" ｜ 📍{_ellipsis(loc, 20)}" if loc else ""

        created_by_uid = None
        cb = getattr(ev, "created_by", None)
        if cb is not None:
            created_by_uid = getattr(cb, "slack_user_id", None) or cb
        created_by_part = f" — 作成:<@{created_by_uid}>" if created_by_uid else ""

        line = f"・{s_hm}-{e_hm}  {title}{created_by_part}{memo_part}{loc_part}"

        by_day.setdefault(day_label, []).append(line)

    # 日付順でまとめて文字列化（日付見出しに🗓️）
    out_lines = []
    for day in sorted(by_day.keys()):
        out_lines.append(f"🗓️ *{day}*")
        out_lines.extend(by_day[day])
    return "\n".join(out_lines)


def _build_event_blocks(rows: list[Event]) -> list[dict]:
    """イベントを '日付見出し + 行 + 編集/削除ボタン' のブロックで返す。"""
    if not rows:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "・今週の予定はありません"}}]

    blocks = []
    day_key = None
    for ev in rows:
        # 時刻・日付（JST）
        s_hm, e_hm, date_jst = _fmt_range_from_utc_naive(ev.start_at, ev.end_at)
        new_day_key = f"{date_jst:%m/%d}（{_weekday_jp(date_jst)}）"

        # 日付見出し（変わった時だけ）
        if new_day_key != day_key:
            day_key = new_day_key
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"🗓️ *{day_key}*"}})

        # 表示テキスト
        title = _ellipsis(getattr(ev, "title", ""), 30)
        memo = getattr(ev, "memo", None)
        loc = getattr(ev, "location", None)
        cb = getattr(ev, "created_by", None)
        created_by_uid = getattr(cb, "slack_user_id", None) if cb else None
        created_by_part = f" — 作成:<@{created_by_uid}>" if created_by_uid else ""
        memo_part = f" ｜ {_ellipsis(memo, 24)}" if memo else ""
        loc_part = f" ｜ 📍{_ellipsis(loc, 20)}" if loc else ""

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"・{s_hm}-{e_hm}  {title}{created_by_part}{memo_part}{loc_part}",
                },
            }
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "style": "primary",
                        "text": {"type": "plain_text", "text": "編集✏️"},
                        "action_id": "event_edit_btn",
                        "value": str(_event_pk_value(ev)),  # ← ここを修正
                    },
                    {
                        "type": "button",
                        "style": "danger",
                        "text": {"type": "plain_text", "text": "削除🗑"},
                        "action_id": "event_delete_btn",
                        "value": str(_event_pk_value(ev)),  # ← ここも修正
                        "confirm": {
                            "title": {"type": "plain_text", "text": "削除の確認"},
                            "text": {"type": "mrkdwn", "text": f"*{title}* を削除します。よろしいですか？"},
                            "confirm": {"type": "plain_text", "text": "削除する"},
                            "deny": {"type": "plain_text", "text": "やめる"},
                        },
                    },
                ],
            }
        )

    return blocks


# Home の blocks
def build_home_blocks(client, week_offset_days: int = 0) -> list:
    today_actual = datetime.now(TZ_JST).date()

    week_base = today_actual + timedelta(days=week_offset_days)
    week_start, week_end = week_base, week_base + timedelta(days=6)

    presence_rows = _fetch_today_presence_rows(today_actual)
    home_n = sum(1 for r in presence_rows if getattr(r, "status", "") == "home")
    away_n = sum(1 for r in presence_rows if getattr(r, "status", "") == "away")
    presence_heading = f"*今日の在宅状況（{today_actual:%m/%d}）*　{home_n}在宅 / {away_n}外出"
    presence_text = _format_presence_text(presence_rows)

    event_rows = _fetch_week_event_rows(week_start, week_end)
    events_text = _format_events_text(event_rows)

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*シェアハウス共同生活管理アプリ*\nスパルタキャンプ最高❗️"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "sharehouse-botの使い方"},
                    "action_id": "AID_OPEN_SHAREHOUSE_BOT_MANUAL",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📖 マニュアル"},
                    # PDFのURL リンク貼り直せば更新可能
                    "url": "https://drive.google.com/file/d/1t3riT_PCh5vqPKxbQNg82AsrVli2BRkf/view?usp=drive_link",
                    "action_id": "open_manuals",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📄 シェアハウス申請書"},
                    # PDFのURL リンク貼り直せば更新可能
                    "url": "https://drive.google.com/file/d/1bG5E1KUM27Sck_a7hMc4zkfhXeEFReDd/view?usp=sharing",
                    "action_id": "open_form",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🏠在宅状況"},
                    "action_id": AID_OPEN_PRESENCE,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️予定を追加"},
                    "action_id": AID_OPEN_EVENT_CREATE,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🧹 掃除チェック"},
                    "action_id": AID_CLEANING_OPEN,
                    "value": "open",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🗂️ 掃除履歴"},
                    "action_id": "cleaning_history",
                    "value": "open",
                },
            ],
        },
        {"type": "divider"},
        {  # 在宅の見出し＋一覧
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{presence_heading}\n{presence_text}"},
        },
    ]

    # blocks.append(
    #     {
    #         "type": "section",
    #         "text": {"type": "mrkdwn", "text": f"*今週の予定（{week_start:%m/%d} 〜 {week_end:%m/%d}）*"},
    #     }
    # )

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*今週の予定（{week_start:%m/%d} 〜 {week_end:%m/%d}）*\n{events_text}",
            },
        }
    )
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "← 前の週"},
                    "action_id": "week_nav_prev",
                    "value": str(week_offset_days - 7),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "今週"},
                    "action_id": "week_nav_now",
                    "value": "0",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "次の週 →"},
                    "action_id": "week_nav_next",
                    "value": str(week_offset_days + 7),
                },
            ],
        }
    )
    blocks.extend(_build_event_blocks(event_rows))

    rendered_at = datetime.now(TZ_JST)
    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"最終更新: {rendered_at:%H:%M}"}],
        }
    )

    return blocks
