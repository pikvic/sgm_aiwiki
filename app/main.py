from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4

from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.gigachat import GigaChat

from app.config import TOKEN

wiki_dir = Path() / "app" / "wiki"
files = [f for f in wiki_dir.iterdir()]

model = GigaChat(credentials=TOKEN, verify_ssl_certs=False)

def search(query, strings):
    result = []
    for s in strings:
        if query.lower() in s.lower():
            result.append(s)
    return result

def get_data(query):
    title = query
    file = wiki_dir / f"{title}.txt"
    text = file.read_text(encoding="utf-8")
    return title, text

def get_init_messages(title, text):
    messages = [
        SystemMessage(
            content=f"""
    Ты будешь отвечать на вопросы о {title}.
    Для ответа на вопрос используй информацию из текста о {title} ниже.
    Если на заданный вопрос нет информации в тексте, попроси уточнить вопрос до трёх раз.
    Если за три раза не удаётся ответить на вопрос, скажи, что в базе данных нет информации по этому вопросу.
    Тебе необходимо давать ответы строго на основе информации из текста, не искажая факты.
    От этого зависят жизни людей и не только.
    Если хорошо справишься с работой - дам тебе денег.
    Первым сообщением выведи приветственное сообщение о том, что ты готов ответить на вопросы о {title} (соблюдай грамматику, орфографию, склонения).
    [Текст о {title}]:
    {text}
    [Конец текста]"""
        )
    ]
    return messages


class ChatMessage(BaseModel):
    role: str
    content: str

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


hello = "Здравствуйте! Я — виртуальный ассистент по работе с базой данных информации о месторождениях России (wiki.geologyscience). Укажите название месторождения, которое вас интересует."
chats = {}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    chat_id = request.cookies.get("chat_id", None)
    message = ChatMessage(role="bot", content=hello)
    response = templates.TemplateResponse("index.html", {"request": request, "messages": [message]})
    
    if not chat_id:
        chat_id = str(uuid4())
        response.set_cookie(key="chat_id", value=chat_id)
    
    chat = None
    chats[chat_id] = {"chat": chat, "messages": [message]}
    return response

@app.post("/chat", response_model=ChatMessage)
async def chat(request: Request, message: ChatMessage):
    chat_id = request.cookies.get("chat_id", None)
    print(chat_id)
    print(message)
    if not chats[chat_id]["chat"]:
        strings = [f.stem for f in files]
        res = search(message.content, strings=strings)
        print(res)
        if not res:
            content = "Такого месторождения нет в базе."
            msg = ChatMessage(role="bot", content=content)
            return msg    
        if len(res) > 1:
            text = ", ".join(res)
            content = f"Пожалуйста, укажите одно из подходящих месторождений: {text}"
            msg = ChatMessage(role="bot", content=content)
            return msg
        if len(res) == 1:
            title, text = get_data(res[0])
            the_chat = get_init_messages(title, text)
            chats[chat_id]["chat"] = the_chat
            content = f"Месторождение выбрано. Задавайте ваши вопросы."
            msg = ChatMessage(role="bot", content=content)
            return msg

    chat_messages = chats[chat_id]["chat"]
    chat_messages.append(HumanMessage(content=message.content))
    print(chat_messages)
    res = model(chat_messages)
    chat_messages.append(res)
    chats[chat_id]["messages"].append(res.content)
    msg = ChatMessage(role="bot", content=res.content)
    return msg

