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
import database_manager

# .env を読み込み
load_dotenv()

# 必須トークンを取得
BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
if not BOT_TOKEN or not APP_TOKEN:
    raise SystemExit("'.env' に SLACK_BOT_TOKEN と SLACK_APP_TOKEN を設定してください。")

# アプリ本体（Botトークン）
app = App(token=BOT_TOKEN)


# ----------------- 修正されたメンションハンドラー -----------------
@app.event("app_mention")
def on_mention(event, say, logger):
    import re

    # メッセージ本文を取得し、メンション部分を除去
    text = event.get("text", "")
    keyword = text.replace(f'<@{app.client.auth_test().get("user_id")}>', "").strip()

    # 日本語のひらがな、記号、句読点などを取り除く
    # 漢字とカタカナ、英数字のみを抽出
    keyword = re.sub(r"[ぁ-んァ-ヶー！？。、\s]+", "", keyword)

    # キーワードが空でないか確認
    if not keyword:
        say("こんにちは！何かお探しですか？キーワードを入力して私にメンションしてください。")
        return

    # データベースを検索
    results = database_manager.search_manuals_by_keyword(keyword)

    # 検索結果があれば返信
    if results:
        for title, body_text in results:
            say(f"*{title}*\n{body_text}")
    else:
        say(f"'{keyword}' に一致するマニュアルは見つかりませんでした。")


# -----------------------------------------------------------------
# 分割ハンドラを登録
register_home(app)
register_manuals(app)
register_presence(app)

# --- ここから追加 ---
# アプリ起動時にデータベースを初期化し、初期データを挿入
database_manager.init_db()
database_manager.insert_initial_data()
# --- ここまで追加 ---


# Socket Mode で起動
if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
