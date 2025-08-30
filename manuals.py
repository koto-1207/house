# manuals.py
from slack_sdk.errors import SlackApiError


def register_manuals(app):
    @app.action("open_manuals")
    def open_manuals(ack, body, client, logger):
        # 0) 3秒以内にACK（必須）
        ack()
        logger.info("[open_manuals] action received")

        # 1) trigger_id を取得（Homeのボタンから来る）
        trigger_id = body.get("trigger_id")
        if not trigger_id:
            logger.error("[open_manuals] trigger_id missing")
            return

        # 2) 表示する内容（まずはハードコードのまま）
        manuals = [
            {
                "title": "ゴミ出しルール",
                "body": "燃えるゴミは *月/木の朝8:00* までに玄関前のカゴへ。ラベル貼付＆袋口を結ぶこと。",
            },
            {
                "title": "静音タイム",
                "body": "*22:00〜7:00* は通話・音楽・ドアの開閉音に配慮。共用部での打合せは避ける。",
            },
            {
                "title": "共有キッチン",
                "body": "調理後は*5分以内*に片付け。シンク洗浄・コンロ拭き・生ゴミは密封廃棄。",
            },
        ]
        blocks = []
        for m in manuals:
            blocks.extend(
                [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*{m['title']}*\n{m['body']}"}},
                    {"type": "divider"},
                ]
            )
        if blocks:
            blocks.pop()

        # 3) モーダルを開く（失敗時は詳細ログ＋ユーザーにもDMでお知らせ）
        try:
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "マニュアル"},
                    "close": {"type": "plain_text", "text": "閉じる"},
                    "blocks": blocks
                    or [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "まだマニュアルが登録されていません。"},
                        }
                    ],
                },
            )
            logger.info("[open_manuals] views_open ok")
        except SlackApiError as e:
            logger.error(f"[open_manuals] views_open error: {e.response.get('error')}")
            try:
                user_id = body.get("user", {}).get("id")
                if user_id:
                    # DMを開いて簡単なエラーメッセージ（任意の保険）
                    im = client.conversations_open(users=user_id)
                    client.chat_postMessage(
                        channel=im["channel"]["id"],
                        text=f"マニュアルを開けませんでした: `{e.response.get('error')}`",
                    )
            except Exception as ee:
                logger.error(f"[open_manuals] notify error: {ee}")
