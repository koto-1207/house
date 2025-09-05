from database_manager import search_manuals_by_keyword


def register_event_handlers(app):
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
        index = int(index_str) + 1

        results = search_manuals_by_keyword(query)
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        if index >= len(results):
            client.chat_update(
                channel=channel_id, ts=message_ts, text="これ以上の検索結果はありません。", blocks=[]
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
        client.chat_update(channel=channel_id, ts=message_ts, text=f"{title} - {body_text}", blocks=blocks)
