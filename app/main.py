from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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
    
    if not user_id:
        user_id = str(uuid4())
        response = templates.TemplateResponse("index.html", {"request": request, "chats": []})
        response.set_cookie(key="user_id", value=user_id)
    else:
        user_chats = mongo.get_user_chats(user_id)
        for chat in user_chats:
            title = chat['messages'][0]['content'] if len(chat['messages']) < 2 else chat['messages'][1]['content']
            chat["title"] = f"{title}..."
            chat["created"] = chat["chat_created"].strftime("%Y-%m-%d %H:%M:%S")
            chat["url"] = f'chats/{chat["chat_id"]}'
        response = templates.TemplateResponse("index.html", {"request": request, "chats": user_chats})
    
    return response

@app.get("/chats/new", response_class=HTMLResponse)
async def new_chat(request: Request):
    user_id = request.cookies.get("user_id", None)

    if not user_id:
        return RedirectResponse("/")    

    user_chats = mongo.get_user_chats(user_id)
    for chat in user_chats:
        title = chat['messages'][0]['content'] if len(chat['messages']) < 2 else chat['messages'][1]['content']
        chat["title"] = f"{title}..."
        chat["created"] = chat["chat_created"].strftime("%Y-%m-%d %H:%M:%S")
        chat["url"] = f'chats/{chat["chat_id"]}'

    message = ChatMessage(role="bot", content=hello, created=now())
    chat_id = str(uuid4())
    chat_created = now()
    chat = {
        "chat_id": chat_id,
        "chat_created": chat_created,
        "user_id": user_id,
        "messages": [message.model_dump()],
        "model_messages": []
    }
    mongo.create_chat(chat)

    response = templates.TemplateResponse("chat.html", {"request": request, "messages": [message], "chats": user_chats})
    response.set_cookie(key="chat_id", value=chat_id)
    return response

@app.get("/chats/{chat_id}", response_class=HTMLResponse)
async def new_chat(chat_id: str, request: Request):
    user_id = request.cookies.get("user_id", None)
    if not user_id:
        return RedirectResponse("/")    
    user_chats = mongo.get_user_chats(user_id)
    for chat in user_chats:
        title = chat['messages'][0]['content'] if len(chat['messages']) < 2 else chat['messages'][1]['content']
        chat["title"] = f"{title[:50]}..."
        chat["created"] = chat["chat_created"].strftime("%Y-%m-%d %H:%M:%S")
        chat["url"] = f'chats/{chat["chat_id"]}'
    
    chat = mongo.get_chat(chat_id)
    messages = chat["messages"]
    response = templates.TemplateResponse("chat.html", {"request": request, "messages": messages, "chats": user_chats})
    response.set_cookie(key="chat_id", value=chat_id)
    return response


@app.post("/chats", response_model=ChatMessage)
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


