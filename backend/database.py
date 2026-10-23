from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine

engine = create_engine(f'sqlite:///database.db', echo = False)

class Base(DeclarativeBase):
    pass
