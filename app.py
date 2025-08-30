# これから頑張ろう！！

# app.py
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError  # ログ出力用（必要に応じて）

from home import register_home  # house直下のファイルからインポート
from manuals import register_manuals  # 同上

# .env を読み込み
load_dotenv()

# 必須トークンを取得
BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
if not BOT_TOKEN or not APP_TOKEN:
    raise SystemExit("'.env' に SLACK_BOT_TOKEN と SLACK_APP_TOKEN を設定してください。")

# アプリ本体（Botトークン）
app = App(token=BOT_TOKEN)


# 動作確認用：メンションに挨拶
@app.event("app_mention")
def on_mention(event, say, logger):
    user = event.get("user")
    say(f"こんにちは <@{user}> さん！ :wave:\nセットアップ完了です。")


# 分割ハンドラを登録
register_home(app)
register_manuals(app)

# Socket Mode で起動
if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
