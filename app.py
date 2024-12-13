import streamlit as st
import yaml
from utils import vectorize_text, find_most_similar, ask_question, get_docs_list

# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)


def main():
    st.title('Document Search Chatbot')

    # ドキュメントとそのベクトルを取得
    docs = get_docs_list(config['google_drive']['folder_id'])
    contents = [doc['content'] for doc in docs]
    vectors = [vectorize_text(content) for content in contents]

    # チャット履歴の初期化
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーの入力を処理
    if user_input := st.chat_input('メッセージを入力してください:'):
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        question_vector = vectorize_text(user_input)
        similar_documents = find_most_similar(question_vector, vectors, contents)
        answer = ask_question(user_input, similar_documents)
        
        response = f"{answer}\n\n参照したドキュメント:\n"
        for doc in docs:
            if doc['content'] in similar_documents:
                response += f"- [{doc['name']}]({doc['url']})\n"
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


if __name__ == "__main__":
    main()