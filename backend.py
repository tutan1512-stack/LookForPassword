from sqlalchemy.orm import DeclarativeBase, sessionmaker, mapped_column, relationship, Mapped, session
from sqlalchemy import create_engine, String, Integer, ForeignKey

engine = create_engine(f'sqlite:///database.db', echo = True)
session_orm = sessionmaker(bind = engine, expire_on_commit=True)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(15), nullable=False)
    password: Mapped[str] = mapped_column(String(30), nullable=False)

    us_to_posts = relationship('UserPost',back_populates='author')
    # мы явно указываем переменную, которая имеет
    # в типе данных List(список) с указанием на ассоциативную сущность,
    # хранящую все записи присущуее для конкретного объекта класса User

    def __str__(self) -> str:
        print(f'{self.id=}// {self.login=}// {self.password=};; ')

class Post(Base):
    __tablename__ = 'posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50), nullable=True)
    text:Mapped[str] = mapped_column(String(255), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    us_to_posts = relationship('UserPost',back_populates='posts')

    def __str__(self) -> str:
        print(f'{self.id=} // {self.title=} //{self.text=} // {self.author_id}')


class UserPost(Base):
    __tablename__ = 'users_to_posts'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    post_id:Mapped[int] = mapped_column(ForeignKey('posts.id'), primary_key=True)

    author = relationship('User', back_populates='us_to_posts')
    posts = relationship('Post',back_populates = 'us_to_posts')


Base.metadata.create_all(engine)

with session_orm() as session:
    user1 = User(id = 1, login = 'admin', password = 'admin')
    post1 = Post(id =1, title='Гойда идет', text = 'Пу-пу-пу-пу', author_id = 1)
    session.add(user1)
    session.add(post1)
    session.commit

    print(session.get(User, 1))
