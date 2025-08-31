# home.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from splite_db_presence import PresenceLog


def register_home(app):
    @app.event("app_home_opened")
    def on_home_opened(event, client, logger):
        user_id = event["user"]
        tz = ZoneInfo("Asia/Tokyo")
        today_jst = datetime.now(tz).date()
        week_start = today_jst
        week_end = today_jst + timedelta(days=6)
        rows = (PresenceLog.select(PresenceLog, PresenceLog.user).where(PresenceLog.date == today_jst))
        label = {"home": "在宅🏠", "away": "外出🚶"}
        lines = []
        for r in rows:
            uid = r.user.slack_user_id  # <@UXXXX> 用
            line = f"・<@{uid}> — {label.get(r.status, r.status)}"
            if r.note:
                line += f"｜{r.note}"
            lines.append(line)
        presence_text = "\n".join(lines) if lines else "・まだ登録がありません"
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*シェアハウス共同生活管理アプリ*\n機能を追加していく",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "マニュアルを見る"},
                                "action_id": "open_manuals",
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "在宅状況"},
                                "action_id": "open_presence",
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "予定を追加"},
                                "action_id": "open_event_create",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• 掃除チェック（まだ）\n• マニュアル閲覧／予定追加（今ここ）",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*今日の在宅状況（{today_jst:%m/%d}）*\n"
                            f"・（ここに在宅状況一覧が入るといいな〜）",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*今日の在宅状況（{today_jst:%m/%d}）*\n{presence_text}"
                        },
                    },
                ],
            },
        )
