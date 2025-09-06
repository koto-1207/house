# nav.py
def register_nav(app):
    from ui_builders import build_home_blocks

    def _handle_week_nav(ack, body, client, logger):
        ack()
        user_id = body["user"]["id"]
        try:
            new_offset = int(body["actions"][0]["value"])
        except Exception as e:
            logger.warning(f"[week_nav] invalid value: {body['actions'][0].get('value')} ({e})")
            new_offset = 0

        client.views_publish(
            user_id=user_id,
            view={"type": "home", "blocks": build_home_blocks(client, week_offset_days=new_offset)},
        )

    @app.action("week_nav_prev")
    def week_nav_prev(ack, body, client, logger):
        _handle_week_nav(ack, body, client, logger)

    @app.action("week_nav_now")
    def week_nav_now(ack, body, client, logger):
        _handle_week_nav(ack, body, client, logger)

    @app.action("week_nav_next")
    def week_nav_next(ack, body, client, logger):
        _handle_week_nav(ack, body, client, logger)
