from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4
from app.mongo import MongoAPI
import datetime
from app.rag import query

from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models.gigachat import GigaChat

from app.config import TOKEN


wiki_dir = Path() / "app" / "wiki"
files = [f for f in wiki_dir.iterdir()]

model = GigaChat(credentials=TOKEN, verify_ssl_certs=False)
mongo = MongoAPI()

class ChatMessage(BaseModel):
    role: str
    content: str
    created: datetime.datetime

class ChatMessageIn(BaseModel):
    role: str
    content: str


def now():
    return datetime.datetime.now(datetime.timezone.utc)


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

hello = "Здравствуйте! Я — виртуальный ассистент по работе с базой данных информации о месторождениях России (wiki.geologyscience). Задавайте вопросы, которые Вас интересуют. Если информация есть в базе, я отвечу."
chats = {}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    user_id = request.cookies.get("user_id", None)

    # chat_id = request.cookies.get("chat_id", None)
    message = ChatMessage(role="bot", content=hello, created=now())
    response = templates.TemplateResponse("index.html", {"request": request, "messages": [message]})
    
    if not user_id:
        user_id = str(uuid4())
        response.set_cookie(key="user_id", value=user_id)
    
    chat_id = str(uuid4())
    chat_created = now()
    response.set_cookie(key="chat_id", value=chat_id)
    chat = {
        "chat_id": chat_id,
        "chat_created": chat_created,
        "user_id": user_id,
        "messages": [message.model_dump()],
        "model_messages": []
    }

    mongo.create_chat(chat)
    # chat = None
    # chats[chat_id] = {"chat": chat, "messages": [message]}
    return response

@app.post("/chat", response_model=ChatMessage)
async def chat(request: Request, message: ChatMessageIn):
    user_id = request.cookies.get("user_id", None)
    chat_id = request.cookies.get("chat_id", None)
    
    chat = mongo.get_chat(chat_id)
    message = ChatMessage(role=message.role, content=message.content, created=now())
    mongo.add_message(chat_id, message.model_dump())

    if not chat["model_messages"]:
        prompt, response_text = query(message.content)
        human = {"role": "human", "content": prompt.content}
        ai = {"role": "ai", "content": response_text.content}
        mongo.add_model_message(chat_id, human)
        mongo.add_model_message(chat_id, ai)
        response_message = ChatMessage(role="bot", content=response_text.content, created=now())
        mongo.add_message(chat_id, response_message.model_dump())
        return response_message

    messages = []
    for msg in chat["model_messages"]:
        if msg["role"] == "human":
            new_message = HumanMessage(content=msg["content"])
            messages.append(new_message)
        if msg["role"] == "ai":
            new_message = AIMessage(content=msg["content"])
            messages.append(new_message)
    new_message = HumanMessage(content=message.content)
    mongo.add_model_message(chat_id, {"role": "human", "content": new_message.content})
    
    messages.append(new_message)
    res = model(messages)
    mongo.add_model_message(chat_id, {"role": "ai", "content": res.content})

    response_message = ChatMessage(role="bot", content=res.content, created=now())        
    mongo.add_message(chat_id, response_message.model_dump())

    return response_message
    # chat_id = request.cookies.get("chat_id", None)
    # print(chat_id)
    # print(message)
    # if not chats[chat_id]["chat"]:
    #     strings = [f.stem for f in files]
    #     res = search(message.content, strings=strings)
    #     print(res)
    #     if not res:
    #         content = "Такого месторождения нет в базе."
    #         msg = ChatMessage(role="bot", content=content)
    #         return msg    
    #     if len(res) > 1:
    #         text = ", ".join(res)
    #         content = f"Пожалуйста, укажите одно из подходящих месторождений: {text}"
    #         msg = ChatMessage(role="bot", content=content)
    #         return msg
    #     if len(res) == 1:
    #         title, text = get_data(res[0])
    #         the_chat = get_init_messages(title, text)
    #         chats[chat_id]["chat"] = the_chat
    #         content = f"Месторождение выбрано. Задавайте ваши вопросы."
    #         msg = ChatMessage(role="bot", content=content)
    #         return msg

    # chat_messages = chats[chat_id]["chat"]
    # chat_messages.append(HumanMessage(content=message.content))
    # print(chat_messages)
    # res = model(chat_messages)
    # chat_messages.append(res)
    # chats[chat_id]["messages"].append(res.content)
    # msg = ChatMessage(role="bot", content=res.content)
    # return msg

