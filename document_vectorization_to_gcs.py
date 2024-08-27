import os
import json
import yaml
from google.oauth2 import service_account
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from openai import OpenAI
import io

# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

def setup_clients():
    # サービスアカウントの認証情報を読み込む
    credentials = service_account.Credentials.from_service_account_file(
        config['google']['service_account_file'],
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )

    # OpenAI API Keyを環境変数から設定
    os.environ["OPENAI_API_KEY"] = config['openai']['api_key']

    # クライアントの初期化
    drive_service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
    openai_client = OpenAI()
    storage_client = storage.Client.from_service_account_json(config['google']['service_account_file'])
    
    print("クライアント初期化完了。")
    return drive_service, openai_client, storage_client

def download_document(drive_service, file_id):
    request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def list_documents_in_folder(drive_service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    return results.get('files', [])

def vectorize_text(openai_client, text):
    response = openai_client.embeddings.create(
        input=text, 
        model=config['openai']['embedding_model']
    )
    return response.data[0].embedding

def save_to_gcs(storage_client, data, filename):
    bucket = storage_client.bucket(config['gcs']['bucket_name'])
    blob = bucket.blob(filename)
    blob.upload_from_string(json.dumps(data))
    print(f"{filename} をGCSバケット {config['gcs']['bucket_name']} に保存しました")

def process_documents():
    drive_service, openai_client, storage_client = setup_clients()

    folder_id = config['google_drive']['folder_id']
    print(f"FOLDER_ID: {folder_id}")
    print(f"GCS_BUCKET_NAME: {config['gcs']['bucket_name']}")

    documents = list_documents_in_folder(drive_service, folder_id)
    print(f"フォルダ内のドキュメント数: {len(documents)}")
    for doc in documents:
        print(f"ドキュメントID: {doc['id']}, 名前: {doc['name']}")

    document_vectors = {}

    for document in documents:
        doc_id, doc_name = document['id'], document['name']
        print(f"ドキュメント処理中: {doc_name}")
        
        doc_content = download_document(drive_service, doc_id)
        print(f"内容の長さ: {len(doc_content)} 文字")
        
        vector = vectorize_text(openai_client, doc_content)
        document_vectors[doc_name] = vector
        print(f"ベクトルの長さ: {len(vector)}")
        print("---")

    print(f"処理したドキュメントの総数: {len(document_vectors)}")

    # ドキュメントベクトルをGCSに保存
    save_to_gcs(storage_client, document_vectors, config['gcs']['document_vectors_file'])

    # 例：各ベクトルの最初の10要素を表示
    for doc_name, vector in document_vectors.items():
        print(f"ドキュメント: {doc_name}, ベクトル: {vector[:10]}...")

if __name__ == "__main__":
    process_documents()