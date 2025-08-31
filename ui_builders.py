# ui_builders.py
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from peewee import JOIN

# ← あなたのモデル定義に合わせて調整してください
# 例：splite_db_presence.py に User / PresenceLog / Event がある想定
from splite_db_presence import User, PresenceLog, Event

# ===== 定数 =====
TZ_JST = ZoneInfo("Asia/Tokyo")
TZ_UTC = ZoneInfo("UTC")

# action_id を定数化（typo防止）
AID_OPEN_MANUALS = "open_manuals"
AID_OPEN_PRESENCE = "open_presence"
AID_OPEN_EVENT_CREATE = "open_event_create"


# ===== 小さなユーティリティ =====
def _weekday_jp(d: datetime.date) -> str:
    # 0=Mon ... 6=Sun
    return "月火水木金土日"[d.weekday()]


def _to_utc_naive(dt_jst: datetime) -> datetime:
    """JST aware -> UTC naive"""
    return dt_jst.astimezone(TZ_UTC).replace(tzinfo=None)


def _utc_naive_to_jst(dt_utc_naive: datetime) -> datetime:
    """UTC naive -> JST aware"""
    return dt_utc_naive.replace(tzinfo=TZ_UTC).astimezone(TZ_JST)


# ===== Presence（今日の在宅） =====
def _fetch_today_presence_rows(today_jst) -> list[PresenceLog]:
    """
    今日分の presence_logs を取得。
    PresenceLog.user は User への FK（to_field=slack_user_id）想定。
    """
    # User を LEFT JOIN して、後で r.user.slack_user_id / r.user.name を参照可能に
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
    lines = []
    seen = set()  # 同一ユーザーの重複表示を避けたい場合（最新のみ残す）
    for r in rows:
        uid = getattr(r.user, "slack_user_id", None) or r.user  # FKが文字列でも安全に
        if uid in seen:
            continue
        seen.add(uid)
        line = f"・<@{uid}> — {label.get(r.status, r.status)}"
        if r.note:
            line += f"｜{r.note}"
        lines.append(line)
    # 最新順に並んでいるので、そのまま表示
    return "\n".join(lines)


# ===== Events（今週の予定） =====
def _fetch_week_event_rows(week_start_jst, week_end_jst) -> list[Event]:
    """
    JST の [week_start 00:00, week_end+1 00:00) を UTC に変換して、その範囲の Event を取得。
    """
    # JST 範囲の下限・上限（上限は翌日 00:00）
    lower_jst = datetime.combine(week_start_jst, time(0, 0), tzinfo=TZ_JST)
    upper_jst = datetime.combine(week_end_jst + timedelta(days=1), time(0, 0), tzinfo=TZ_JST)

    lower_utc_naive = _to_utc_naive(lower_jst)
    upper_utc_naive = _to_utc_naive(upper_jst)

    rows = (
        Event.select(Event, User)
        .join(
            User, JOIN.LEFT_OUTER
        )  # Event.created_by が User FK（to_field=slack_user_id or id どちらでもOK）
        .where((Event.start_at >= lower_utc_naive) & (Event.start_at < upper_utc_naive))
        .order_by(Event.start_at)
    )
    return list(rows)


def _format_events_text(rows: list[Event]) -> str:
    if not rows:
        return "・今週の予定はありません"

    lines = []
    for ev in rows:
        # UTC naive を JST 表示に変換
        s_jst = _utc_naive_to_jst(ev.start_at)
        e_jst = _utc_naive_to_jst(ev.end_at)

        day = f"{s_jst:%m/%d}（{_weekday_jp(s_jst.date())}）"
        t_range = f"{s_jst:%H:%M}-{e_jst:%H:%M}"
        created_by_uid = None

        # created_by が FK の場合に slack_user_id を取り出す（FKが文字列でもOKにする）
        cb = getattr(ev, "created_by", None)
        if cb is not None:
            created_by_uid = getattr(cb, "slack_user_id", None) or cb

        created_by_text = f" — 作成:<@{created_by_uid}>" if created_by_uid else ""
        memo_text = f" ｜ {ev.memo}" if getattr(ev, "memo", None) else ""

        lines.append(f"・{day} {t_range}  {ev.title}{created_by_text}{memo_text}")

    return "\n".join(lines)


# ===== Home の blocks ビルダー（ここだけを各所から呼ぶ） =====
def build_home_blocks(client) -> list:
    """
    Homeタブの blocks を一括で構築して返す。
    - 日付計算（JST）
    - DBからデータ取得
    - 表示用テキスト整形
    - Block Kit JSON の組み立て
    """
    today = datetime.now(TZ_JST).date()
    week_start, week_end = today, today + timedelta(days=6)

    presence_rows = _fetch_today_presence_rows(today)
    presence_text = _format_presence_text(presence_rows)

    event_rows = _fetch_week_event_rows(week_start, week_end)
    events_text = _format_events_text(event_rows)

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*シェアハウス共同生活管理アプリ*\n最小構成が動いています！"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "マニュアルを見る"},
                    "action_id": AID_OPEN_MANUALS,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "在宅状況"},
                    "action_id": AID_OPEN_PRESENCE,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "予定を追加"},
                    "action_id": AID_OPEN_EVENT_CREATE,
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*今日の在宅状況（{today:%m/%d}）*\n{presence_text}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*今週の予定（{week_start:%m/%d} 〜 {week_end:%m/%d}）*\n{events_text}",
            },
        },
    ]
    return blocks
