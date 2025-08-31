# events.py
def register_events(app):
    @app.action("open_event_create")
    def open_event_create(ack, body, client, logger):
        ack()
        trigger_id = body.get("trigger_id")
        if not trigger_id:
            logger.error("[open_event_create] trigger_id missing")
            return

        # まずは仮モーダル（後でフォームに置き換え）
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "予定を追加（仮）"},
                "close": {"type": "plain_text", "text": "閉じる"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*プレースホルダ*\nここにタイトル/日付/開始/終了/メモの入力欄が入る",
                        },
                    }
                ],
            },
        )
