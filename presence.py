# presence.py
def register_presence(app):
    @app.action("open_presence")
    def open_presence(ack, body, client, logger):
        ack()  # 応答（必須）

        trigger_id = body.get("trigger_id")
        if not trigger_id:
            logger.error("[open_presence] trigger_id missing")
            return

        # 仮の表示（プレースホルダ）
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "在宅状況（仮）"},
                "close": {"type": "plain_text", "text": "閉じる"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*在宅状況[●●]*\nここに在宅状況を入れれるようにpresence.pyにコードを書く",
                        },
                    }
                ],
            },
        )
