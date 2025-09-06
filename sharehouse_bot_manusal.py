# sharehouse_bot_manusal.py
from slack_sdk.errors import SlackApiError


def register_bot_manuals(app):
    @app.action("AID_OPEN_SHAREHOUSE_BOT_MANUAL")
    def open_manuals(ack, body, client, logger):
        ack()
        logger.info("[open_manuals] action received")

        trigger_id = body.get("trigger_id")
        if not trigger_id:
            logger.error("[open_manuals] trigger_id missing")
            return

        # ここに「sharehouse-botの使い方」をモーダル表示
        usage_manual_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*sharehouse-botの使い方*"}},
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "1️⃣ botチャンネルを使って質問してください。",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "2️⃣ メンションで質問\n- チャンネルやDMで `@sharehouse-bot` と入力\n- 例: `@sharehouse-bot 掃除",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "3️⃣ 単語で検索\n- 入力内容から自動でキーワードを抽出して検索",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "4️⃣ 近い回答を返す\n- 内部データベース（MANUALS_DATA）から類似度の高い回答を提示",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "💡 ポイント: もし結果が出ない場合は、別の単語でもお試しください🙇\n または、マニュアルをご確認いただけますと幸いです。",
                },
            },
        ]

        try:
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "使い方"},
                    "close": {"type": "plain_text", "text": "閉じる"},
                    "blocks": usage_manual_blocks,
                },
            )
            logger.info("[open_manuals] views_open ok")
        except SlackApiError as e:
            logger.error(f"[open_manuals] views_open error: {e.response.get('error')}")
            try:
                user_id = body.get("user", {}).get("id")
                if user_id:
                    im = client.conversations_open(users=user_id)
                    client.chat_postMessage(
                        channel=im["channel"]["id"],
                        text=f"マニュアルを開けませんでした: `{e.response.get('error')}`",
                    )
            except Exception as ee:
                logger.error(f"[open_manuals] notify error: {ee}")
