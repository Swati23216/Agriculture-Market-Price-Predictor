import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file into environment

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
    DEBUG = False
    TESTING = False

    # ✅ This is the correct key for Flask-PyMongo
    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb+srv://Swati:swati123@cluster0.4iyznj8.mongodb.net/flask?retryWrites=true&w=majority&appName=Cluster0"
    )
