from openai import OpenAI
import yaml
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.cloud import storage
import json
import time

def log_message(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# config.ymlファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

log_message("設定ファイルを読み込みました。")

# Google Cloud Storageクライアントの作成
credentials = Credentials.from_service_account_file(config['google']['service_account_file'])
storage_client = storage.Client(credentials=credentials)
openai_client = OpenAI(api_key=config['openai']['api_key'])
bucket = storage_client.bucket(config['gcs']['bucket_name'])

log_message("Google Drive APIとGoogle Cloud Storageの認証が完了しました。")

# Google Drive APIクライアントの作成
drive_service = build('drive', 'v3', credentials=credentials)

# フォルダ内のすべてのGoogleドキュメントを取得
log_message(f"フォルダID: {config['google_drive']['folder_id']} からドキュメントを取得中...")
results = drive_service.files().list(q=f"'{config['google_drive']['folder_id']}' in parents and mimeType='application/vnd.google-apps.document'",
                                    fields="files(id, name)").execute()
documents = results.get('files', [])
log_message(f"{len(documents)}件のドキュメントが見つかりました。")

# 各Googleドキュメントをベクトル化し、GCSに保存
vector_data = {}
for index, document in enumerate(documents, 1):
    doc_id = document['id']
    doc_name = document['name']
    
    log_message(f"処理中 ({index}/{len(documents)}): {doc_name} (ID: {doc_id})")
    
    try:
        # Googleドキュメントのコンテンツを取得
        doc_content = drive_service.files().export(fileId=doc_id, mimeType='text/plain').execute()
        text = doc_content.decode('utf-8')
        log_message(f"  ドキュメントのコンテンツを取得しました。文字数: {len(text)}")
        
        # OpenAI APIを使用してテキストをベクトル化
        response = openai_client.embeddings.create(input=text, model=config['openai']['embedding_model'])
        embeddings = response.data[0].embedding
        log_message(f"  ベクトル化が完了しました。ベクトルの次元数: {len(embeddings)}")
        
        # ベクトルデータを格納
        vector_data[doc_name] = embeddings
    except Exception as e:
        log_message(f"  エラーが発生しました: {str(e)}")
        continue

log_message("すべてのドキュメントの処理が完了しました。")

# ベクトルデータをGCSに保存
log_message(f"ベクトルデータをGCSに保存中... (バケット: {config['gcs']['bucket_name']}, ファイル: {config['gcs']['document_vectors_file']})")
blob = bucket.blob(config['gcs']['document_vectors_file'])
blob.upload_from_string(data=json.dumps(vector_data), content_type='application/json')

log_message(f"処理が完了しました。{len(vector_data)}件のドキュメントがベクトル化され、GCSに保存されました。")