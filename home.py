
# home.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlite_db_presence import PresenceLog
from ui_builders import build_home_blocks


def register_home(app):
    @app.event("app_home_opened")
    def on_home_opened(event, client, logger):
        user_id = event["user"]
        client.views_publish(
            user_id=user_id, view={
                "type": "home", "blocks": build_home_blocks(client)
                }
            )
