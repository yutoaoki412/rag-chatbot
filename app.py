import streamlit as st
import yaml
from utils import vectorize_text, find_most_similar, ask_question, get_docs_list

# 設定ファイルを読み込む
def load_config():
    with open('config.yml', 'r') as file:
        return yaml.safe_load(file)

def main():
    st.title('Document Search Chatbot')

    config = load_config()

    # 初期化
    if 'docs' not in st.session_state:
        st.session_state.docs = get_docs_list(config['google_drive']['folder_id'])
        st.session_state.contents = [doc['content'] for doc in st.session_state.docs]
        st.session_state.vectors = [vectorize_text(content) for content in st.session_state.contents]

    # チャット履歴をセッション状態で保持
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # チャットの表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーの入力を受け取る
    if user_input := st.chat_input('メッセージを入力してください:'):
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 質問をベクトル化
        question_vector = vectorize_text(user_input)
        
        # 最も関連性の高いドキュメントを見つける
        similar_documents = find_most_similar(question_vector, st.session_state.vectors, st.session_state.contents)

        # 質問に対する回答を生成
        answer = ask_question(user_input, similar_documents)
        
        # 回答と参照ドキュメントの情報を追加
        response = f"{answer}\n\n参照したドキュメント:\n"
        for doc in st.session_state.docs:
            if doc['content'] in similar_documents:
                response += f"- [{doc['name']}]({doc['url']})\n"
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

if __name__ == "__main__":
    main()