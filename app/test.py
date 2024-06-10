from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.gigachat import GigaChat
from langchain_community.embeddings import GigaChatEmbeddings
from langchain.vectorstores.chroma import Chroma
from langchain.prompts import ChatPromptTemplate

from config import TOKEN

CHROMA_PATH = r"chroma"

PROMPT_TEMPLATE = """
Ты ассистент для ответа на вопросы о месторождениях. 
Используй информацию о месторождениях, заданную в контексте, для ответа на вопрос. 
Если не знаешь ответ, то так и скажи.
Приведи факты из контекста в ответе.
Ответ должен быть исчерпывающим, на основе контекста, содержать не более десяти предложений.

Вопрос: {question} 

Контекст: {context} 

Ответ:
"""

def main():

    query_text = input("Введите запрос: ")
    
    embedding_function = GigaChatEmbeddings(credentials=TOKEN, verify_ssl_certs=False)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    results = db.similarity_search(query_text, k=5)

    docs = []
    for doc in results:
        title = doc.metadata["source"].split("\\")[-1].split(".")[0]
        content = doc.page_content
        docs.append("\n".join([title, content]))

    context_text = "\n\n---\n\n".join(docs)
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print()
    print("=================PROMT=================")
    print(prompt)
    print()

    model = GigaChat(credentials=TOKEN, verify_ssl_certs=False, verbose=False, )
    response_text = model.invoke(prompt)
        
    print("=============RESPONSE============")
    print()
    print(response_text.content)
    print()

if __name__ == "__main__":
    main()