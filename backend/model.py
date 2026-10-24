from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import  String, Date, ForeignKey, Text
from backend.database import Base, engine
from  datetime import datetime
from typing import List

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(64), nullable=False)

    posts: Mapped[List["Post"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan"  # Если удалить юзера, удалятся и его посты
    )
    def __repr__(self) :
        return f'User({self.id=},  {self.login=},  {self.password=})\n '

class Post(Base):
    __tablename__ = 'posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50), nullable=True)
    text:Mapped[str | None] = mapped_column(Text, nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"))
    data:Mapped[datetime] = mapped_column(Date, default=datetime.now)

    author: Mapped['User'] = relationship(back_populates='posts')

    def __repr__(self) :
        return f'Post({self.id=} ,  {self.title=} , {self.text=} ,  {self.data} , [ {self.author_id=} ,  {self.author.login=}]) \n'

Base.metadata.create_all(engine)



