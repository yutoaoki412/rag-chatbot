import streamlit as st
import yaml
from utils import load_vectors_from_gcs, vectorize_text, find_most_similar, ask_question


# 設定ファイルを読み込む
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

def main():
    st.title(config['streamlit']['title'])

    # GCSからドキュメントをベクトル化したものをロード
    document_vectors = load_vectors_from_gcs()
    
    # チャット履歴をセッション状態で保持
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # チャットの表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーの入力を受け取る
    if user_input := st.chat_input(config['streamlit']['input_placeholder']):
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 質問をベクトル化
        question_vector = vectorize_text(user_input)
        
        # 最も関連性の高いドキュメントを見つける
        most_similar_document = find_most_similar(question_vector, document_vectors)
        context = document_vectors.get(most_similar_document, "")

        # 質問に対する回答を生成
        answer = ask_question(user_input, context)
        
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()

if __name__ == "__main__":
    main()