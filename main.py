from fastapi import FastAPI, Request, Response
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
import yaml
from utils import load_vectors_from_gcs, vectorize_text, find_most_similar, ask_question
from mangum import Mangum

# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

# Slack Appの初期化
app = App(
    token=config['slack']['bot_token'],
    signing_secret=config['slack']['signing_secret']
)

# GCSからドキュメントをベクトル化したものをロード
document_vectors = load_vectors_from_gcs(config['gcs']['bucket_name'], config['gcs']['document_vectors_file'])

@app.event("app_mention")
async def handle_mention_events(event, say):
    # チャンネルIDをチェック
    if event['channel'] not in config['slack']['allowed_channels']:
        await say("このチャンネルではボットを使用できません。")
        return

    user_input = event['text']
    
    # 質問をベクトル化
    question_vector = await vectorize_text(user_input)
    
    # 最も関連性の高いドキュメントを見つける
    most_similar_document = await find_most_similar(question_vector, document_vectors)
    context = document_vectors.get(most_similar_document, "")
    
    # 質問に対する回答を生成
    answer = await ask_question(user_input, context)
    
    # ユーザーに回答を送信
    await say(answer)

# FastAPIアプリケーション
api = FastAPI()
handler = SlackRequestHandler(app)

@api.post("/slack/events")
async def endpoint(req: Request):
    return await handler.handle(req)

# Mangumハンドラの作成
mangum_handler = Mangum(api)

# Cloud Functions用のエントリーポイント
def slack_bot(request):
    return mangum_handler(request)