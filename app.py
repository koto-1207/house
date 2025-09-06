# app.py
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from home import register_home
from manuals import register_manuals
from presence import register_presence
from splite_db_presence import init_db
from events import register_events
from home_nav import register_nav
from event_handlers import register_event_handlers
from clean_list import register_clean_list

# .env を読み込み
load_dotenv()
init_db()

# トークン
BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
if not BOT_TOKEN or not APP_TOKEN:
    raise SystemExit("'.env' に SLACK_BOT_TOKEN と SLACK_APP_TOKEN を設定してください。")

# アプリ本体
app = App(token=BOT_TOKEN)

# --- ハンドラ登録（register_* で統一） ---
register_home(app)
register_manuals(app)
register_presence(app)
register_events(app)
register_nav(app)
register_event_handlers(app)  # ← メンション検索などをここに集約
register_clean_list(app)

# Socket Mode で起動
if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
