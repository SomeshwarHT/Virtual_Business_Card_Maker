import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

IAM_PATH = os.getenv("IAM_PATH", "")
BASE_PATH = os.getenv("BASE_PATH", "")
IAM_AUTH_HEAD_KEY = os.getenv("IAM_AUTH_HEAD_KEY", "A853DG1VNKaEEMBzuP5HDBTQVVAmTX2BPiT5j2Bd")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    IAM_PATH = IAM_PATH
    BASE_PATH = BASE_PATH
    IAM_AUTH_HEAD_KEY = IAM_AUTH_HEAD_KEY

    # GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    # GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
