# これから頑張ろう！！

# app.py
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError  # ログ出力用（必要に応じて）
from home import register_home  # house直下のファイルからインポート
from manuals import register_manuals  # 同上
from presence import register_presence
from database_manager import init_db, insert_initial_data, search_manuals_by_keyword

# DB 初期化
init_db()
insert_initial_data()
# メンションの検索結果をユーザーごとに保持
user_results = {}

# .env を読み込み
load_dotenv()

# 必須トークンを取得
BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
if not BOT_TOKEN or not APP_TOKEN:
    raise SystemExit("'.env' に SLACK_BOT_TOKEN と SLACK_APP_TOKEN を設定してください。")

# アプリ本体（Botトークン）
app = App(token=BOT_TOKEN)


@app.event("app_mention")
def on_mention(event, say):
    text = event.get("text", "")
    bot_user_id = app.client.auth_test().get("user_id")
    query = text.replace(f"<@{bot_user_id}>", "").strip()

    if not query:
        say("こんにちは！キーワードを入力して私にメンションしてください。")
        return

    results = search_manuals_by_keyword(query)

    if not results:
        say(text=f"'{query}' に一致するマニュアルは見つかりませんでした。")
        return

    # 最初の結果を送信
    first_title, first_body = results[0]
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{first_title}*\n{first_body}"}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "次の結果"},
                    "action_id": "next_manual",
                    "value": f"0|{query}",
                }
            ],
        },
    ]
    say(text=f"{first_title} - {first_body}", blocks=blocks)


@app.action("next_manual")
def handle_next_manual(ack, body, client):
    ack()
    value = body["actions"][0]["value"]
    index_str, query = value.split("|")
    index = int(index_str) + 1  # 次の結果へ

    results = search_manuals_by_keyword(query)

    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    if index >= len(results):
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="これ以上の検索結果はありません。",
            blocks=[]
        )
        return

    title, body_text = results[index]
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{body_text}"}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "次の結果"},
                    "action_id": "next_manual",
                    "value": f"{index}|{query}",
                }
            ],
        },
    ]
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"{title} - {body_text}",
        blocks=blocks
    )



# 分割ハンドラを登録
register_home(app)
register_manuals(app)
register_presence(app)

# Socket Mode で起動
if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
