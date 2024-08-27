import os
import yaml
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from utils import load_vectors_from_gcs, vectorize_text, find_most_similar, ask_question

# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

# Slack Appの初期化
app = App(
    token=config['slack']['bot_token'],
    signing_secret=config['slack']['signing_secret']
)

# GCSからドキュメントをベクトル化したものをロード
document_vectors = load_vectors_from_gcs()

@app.event("app_mention")
def handle_mention_events(event, say):
    # チャンネルIDをチェック
    if event['channel'] not in config['slack']['allowed_channels']:
        say("このチャンネルではボットを使用できません。")
        return

    user_input = event['text']
    
    # 質問をベクトル化
    question_vector = vectorize_text(user_input)
    
    # 最も関連性の高いドキュメントを見つける
    most_similar_document = find_most_similar(question_vector, document_vectors)
    context = document_vectors.get(most_similar_document, "")
    
    # 質問に対する回答を生成
    answer = ask_question(user_input, context)
    
    # ユーザーに回答を送信
    say(answer)

if __name__ == "__main__":
    handler = SocketModeHandler(app, config['slack']['app_token'])
    handler.start()