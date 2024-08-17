import os
from dotenv import load_dotenv
import yaml
from google.cloud import storage
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# .envファイルを読み込む
load_dotenv()

# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

# 環境変数を取得
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# クライアントの初期化
openai_client = OpenAI(api_key=OPENAI_API_KEY)
storage_client = storage.Client(GOOGLE_APPLICATION_CREDENTIALS)

def load_vectors_from_gcs():
    """GCSからドキュメントベクトルをロードする"""
    bucket = storage_client.bucket(config['gcs']['bucket_name'])
    blob = bucket.blob(config['gcs']['document_vectors_file'])
    data = yaml.safe_load(blob.download_as_string())
    return data

def vectorize_text(text):
    """テキストをベクトル化する"""
    response = openai_client.embeddings.create(
        input=text, 
        model=config['openai']['embedding_model']
    )
    return response.data[0].embedding

def find_most_similar(question_vector, vectors):
    """最も類似度の高いドキュメントを見つける"""
    similarities = {
        doc_name: cosine_similarity([question_vector], [vector])[0][0]
        for doc_name, vector in vectors.items()
    }
    return max(similarities, key=similarities.get)

def ask_question(question, context):
    """質問に対する回答を生成する"""
    messages = [
        {"role": "system", "content": config['system_prompt']},
        {"role": "user", "content": f"質問: {question}\n\n情報: {context}"}
    ]
    
    response = openai_client.chat.completions.create(
        model=config['openai']['chat_model'],
        messages=messages
    )

    return response.choices[0].message.content