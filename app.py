# これから頑張ろう！！

# app.py
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# from slack_sdk.errors import SlackApiError  # ログ出力用（必要に応じて）
from home import register_home  # house直下のファイルからインポート
from manuals import register_manuals  # 同上
from presence import register_presence
from clean_list import register_clean_list

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
def on_mention(event, say, client):
    user = event.get("user")
    channel = event.get("channel")

    # メンションへの返事
    say(f"こんにちは <@{user}> さん！ :wave:\nセットアップ完了です。")

    # チャンネルに「お掃除チェック」ボタンを送る
    client.chat_postMessage(
        channel=channel,
        blocks=[
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "お掃除チェック"},
                        "action_id": "check_cleaning",
                    }
                ],
            }
        ],
        text="お掃除チェックを開始します",
    )


@app.event("app_home_opened")
def update_home_view(event, client, logger):
    user_id = event["user"]
    logger.info(f"App Home opened by user {user_id}")

    client.views_publish(
    user_id=user_id,
    view={
        "type": "home",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*シェアハウス用共通管理アプリ*\nがんばって機能を作ります"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "マニュアルをみる"},
                        "action_id": "view_manuals"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "在宅状況"},
                        "action_id": "check_presence"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "お掃除チェック"},
                        "action_id": "check_cleaning"
                    }
                ]
            }
        ]
    }
)


# 分割ハンドラを登録
register_home(app)
register_manuals(app)
register_presence(app)
register_clean_list(app)


# Socket Mode で起動
if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
