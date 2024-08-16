# 現状はドキュメントを追加するたびに再実行のフローの想定のため、Google Colab上で実行することを想定

import os
import json
from google.colab import auth, userdata, drive # type: ignore
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from openai import OpenAI
import io


# Google認証を行う（スコープを指定）
auth.authenticate_user()

# 環境変数の設定
os.environ["OPENAI_API_KEY"] = userdata.get('OPENAI_API_KEY')

# Colabのシークレット機能を使用してフォルダID
FOLDER_ID = userdata.get('FOLDER_ID')
GCS_BUCKET_NAME = 'chatbot-input-documents'

# クライアントの初期化
drive_service = build('drive', 'v3', cache_discovery=False)
openai_client = OpenAI()  # API keyは環境変数から自動的に読み込まれます
storage_client = storage.Client()


def download_document(file_id):
    request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    
    return fh.getvalue().decode('utf-8')

def list_documents_in_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()

    return results.get('files', [])

def vectorize_text(text):
    response = openai_client.embeddings.create(
            input=text,
            model = "text-embedding-3-small"
        )
    
    return response.data[0].embedding


def process_documents_in_folder(folder_id):
    documents = list_documents_in_folder(folder_id)
    document_vectors = {}
    
    for document in documents:
        doc_id, doc_name = document['id'], document['name']
        doc_content = download_document(doc_id)
        vector = vectorize_text(doc_content)
        document_vectors[doc_name] = vector
    
    return document_vectors


def save_to_gcs(data, filename):
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(json.dumps(data))
    print(f"Saved {filename} to GCS bucket {GCS_BUCKET_NAME}")


def main():
    document_vectors = process_documents_in_folder(FOLDER_ID)
    
    # Save document vectors to GCS
    save_to_gcs(document_vectors, 'document_vectors.json')
    
    # Example: Print first 10 elements of each vector
    for doc_name, vector in document_vectors.items():
        print(f"Document: {doc_name}, Vector: {vector[:10]}...")

if __name__ == "__main__":
    main()