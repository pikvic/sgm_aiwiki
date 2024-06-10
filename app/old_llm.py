from pydantic import BaseModel
from pathlib import Path


wiki_dir = Path() / "app" / "wiki"
files = [f for f in wiki_dir.iterdir()]



class ChatMessage(BaseModel):
    role: str
    content: str

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


hello_old = "Здравствуйте! Я — виртуальный ассистент по работе с базой данных информации о месторождениях России (wiki.geologyscience). Укажите название месторождения, которое вас интересует."
