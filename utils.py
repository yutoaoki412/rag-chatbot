import yaml
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity


with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

client = OpenAI(api_key=config['openai']['api_key'])
credentials = Credentials.from_service_account_file(config['google']['service_account_file'])
google_client = build('drive', 'v3', credentials=credentials)


def get_docs_list(folder_id):
    files = google_client.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
        fields="files(id, name)"
    ).execute().get('files', [])

    docs_list = []
    for file in files:
        doc_id = file['id']
        doc_content = google_client.files().export(fileId=doc_id, mimeType='text/plain').execute()
        docs_list.append({
            'name': file['name'],
            'url': f"https://docs.google.com/document/d/{doc_id}/edit",
            'content': doc_content.decode('utf-8')
        })

    return docs_list


def vectorize_text(text):
    response = client.embeddings.create(
        input=text,
        model=config['openai']['embedding_model']
    )
    return response.data[0].embedding


def find_most_similar(question_vector, vectors, documents):
    similarities = []

    for index, vector in enumerate(vectors):
        similarity = cosine_similarity([question_vector], [vector])[0][0]
        similarities.append([similarity, index])

    similarities.sort(reverse=True, key=lambda x: x[0])
    top_documents = [documents[index] for similarity, index in similarities[:2]]

    return top_documents


def ask_question(question, context):
    messages = [
        {"role": "system", "content": "以下の情報のみを使用して回答してください。"},
        {"role": "user", "content": f"質問: {question}\n\n情報: {context}"}
    ]
    
    response = client.chat.completions.create(
        model=config['openai']['chat_model'],
        messages=messages
    )

    return response.choices[0].message.content