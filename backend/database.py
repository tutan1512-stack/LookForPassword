from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
engine = create_engine(f'sqlite:///{DB_PATH}', echo = False)

class Base(DeclarativeBase):
    pass
