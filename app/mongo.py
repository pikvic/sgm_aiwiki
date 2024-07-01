from pymongo import MongoClient
from bson.son import SON
from app.config import MONGO_URL, MONGO_DATABASE


class MongoAPI:
    def __init__(self) -> None:
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[MONGO_DATABASE]
    
    def create_chat(self, chat):
        chat_cursor = self.db["chats"]
        chat_cursor.insert_one(chat)
        
    def add_message(self, chat_id, message):
        chat_cursor = self.db["chats"]
        chat_cursor.update_one({'chat_id': chat_id}, {'$push': {'messages': message}})

    def add_model_message(self, chat_id, message):
        chat_cursor = self.db["chats"]
        chat_cursor.update_one({'chat_id': chat_id}, {'$push': {'model_messages': message}})

    def get_chat(self, chat_id):
        chat_cursor = self.db["chats"]
        result = chat_cursor.find_one({"chat_id": chat_id})
        return result
    
    def get_user_chats(self, user_id):
        chat_cursor = self.db["chats"]
        result = chat_cursor.find({"user_id": user_id})
        return list(result)

    def get_scenes(self):
        result = self.db.scene.find()
        return list(result)
    
    def get_scene(self, name):
        result = self.db.scene.find_one({"name": name})
        print(result)
        return result
