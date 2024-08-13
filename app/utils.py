import os
from dotenv import load_dotenv
import json
from google.cloud import storage
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity


# .envファイルを読み込む
load_dotenv()

# GCSバケットの設定
GCS_BUCKET_NAME = 'chatbot-input-documents'
DOCUMENT_VECTORS_FILE = 'document_vectors.json'

# # 環境変数を取得
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# クライアントの初期化
client = OpenAI(api_key=OPENAI_API_KEY)

# Google Cloud Storage クライアントの初期化
storage_client = storage.Client(GOOGLE_APPLICATION_CREDENTIALS)

def load_vectors_from_gcs(bucket_name=GCS_BUCKET_NAME, filename=DOCUMENT_VECTORS_FILE):
    """GCSからドキュメントベクトルをロードする"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    data = json.loads(blob.download_as_string())
    return data

def vectorize_text(text):
    """テキストをベクトル化する"""
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def find_most_similar(question_vector, vectors):
    """最も類似度の高いドキュメントを見つける"""
    highest_similarity = 0
    most_similar_doc = None

    for doc_name, vector in vectors.items():
        similarity = cosine_similarity([question_vector], [vector])[0][0]
        if similarity > highest_similarity:
            highest_similarity = similarity
            most_similar_doc = doc_name
    
    return most_similar_doc

def ask_question(question, context):
    """質問に対する回答を生成する"""
    messages = [
        {"role": "system", "content": "以下の情報のみを使用して回答してください。"},
        {"role": "user", "content": f"質問: {question}\n\n情報: {context}"}
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content