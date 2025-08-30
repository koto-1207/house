1　github　mainブランチから以下ファイルをローカルにpull
　app.py / home.py / manuals.py / requirements.txt / manifest.json / .gitignore / .env.example

２　.env を用意（.env.exampleにトークン部分を削除した状態を作成）
　　自分専用とチーム共通のトークンをそれぞれ.envに記述(トークンの取得は３、４)
　　SLACK_APP_TOKEN=   # xapp-...（自分専用）
　　SLACK_BOT_TOKEN=   # xoxb-...（チーム共通）※無断ローテ禁止

３　ブラウザで Slack API（開発者サイト）にログイン
　１）ブラウザで https://api.slack.com/apps を開く
　２）右上の Sign in（または Sign in with Slack）をクリック
　３）ワークスペースを選択（share_house）
　ーログインが完了すると、自分のワークスペース用の Your Apps 画面が表示

４　トークンを取得
　1）App-level token（xapp-…）を自分で発行（各自専用）
　　左メニュー Basic Information → いちばん下 App-level tokens
　　Generate Token and Scopes をクリック
　　名前：自分の名前など（例：yourname-dev）
　　Scope：connections:write を追加
　　Generate
　　表示された xapp-... をコピー → .env の SLACK_APP_TOKEN に貼り付け

　2）Bot User OAuth Token（xoxb-…）を確認（チーム共通）
　　左メニュー OAuth & Permissions
　　上部の Tokens for Your Workspace に Bot User OAuth Token（xoxb-...） が表示されます
　　見えない場合：
　　まだアプリがインストールされていない → オーナーに Install を依頼
　　権限ポリシーで見えない → オーナーに安全な手段で共有してもらう
　　注意：勝手に Reinstall（再インストール）しないでください。トークンがローテーションして全員の .env が無効になります。
　　表示された xoxb-... を .env の SLACK_BOT_TOKEN に貼り付け

５　pip Install
 pip install -r requirements.txt
# うまくいかない時は:
# python -m pip install -r requirements.txt
# または macOS で: python3 -m pip install -r requirements.txt

６　slackのshare_houseチームで動作確認
　１）任意のチャネルを作成
　２）sharehouse-botを招待
　　招待の仕方がわからなければ@sharehouse-botでメンションすれば「追加する」と表示されるので追加
　３）動作確認
　　初期では、何かコメントするとこんにちはと表示されるようになっている

