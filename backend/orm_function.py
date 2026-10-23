import backend.function as f
import backend.database as db
import backend.model as m
import  sqlalchemy as sql
import sqlalchemy.orm as sql_orm

post = dict(title="title", text = 'text', author_id=6, data = "0000.00.00" )

session_orm = sql_orm.sessionmaker(bind = db.engine, expire_on_commit=True)

def no_duplicate(session, login,password):
    '''
    Мы передаем на вход данные пользователя и отправляем запрос на бд,
    чтобы сверится, есть ли такая запись. Если нет, то мы пропускаем и сообщаем об этом,
    иначе создаем запись.

    Пароль сверяется не с тем, который ввел пользователь, а с тем что выдала хэш-функция
    '''

    # формируем запрос
    statement = sql.select(sql.exists().
            where(
            (m.User.login == login)
        )
    )

    result = session.scalars(statement)
    if result is  True:
        print('\n[>] Такая запись существует!\n')
        pass

    else:
        hash_password = f.generated_hash(password)
        new_user = m.User(login = login, password = hash_password)
        session.add(new_user)

def comparison(session, login, password):
    '''
    мы падаем в функцию наш логин и хэшированный пароль, сверяем корректность данных в бд
    при совпадении мы возвращаем True, иначе False
    '''
    hash_password = f.generated_hash(password)
    statement = sql.select(
        sql.exists().where(
            m.User.login == login, m.User.password == hash_password
        ))

    result = session.scalar(statement)
    if result is True:
        print('\n[>] Логин и пароль верные!\n')
        return result
    else:
        print('\n[>] Логин или пароль не верны!\n')
        return result

def create_post(session, login):
    '''
        Мы создаем новый пост уже в выбранном аккаунте, т.е. id автора всегда определяется,
        проверка на существования автора не нужна.
    '''
    title_v = input(f"\n[>] Введите название поста: ")
    text_v = input(f"[>] Введите текста поста: ")
    stmt = sql.select(m.User.id).where(
        m.User.login == login
    )
    author_v = session.execute(stmt).scalars().first()

    new_posts = m.Post(title = title_v, text = text_v, author_id = author_v)
    session.add(new_posts)
    print(f"\n[>] Пост добавлен!\n")

    return 0

def get_post(session, login):
    '''
        В текущей сессии мы выводим все записи для выбранной модели
    '''
    statement = (sql.select(m.Post)
    .where(
                 m.Post.author.has( m.User.login == login)
        # метод has() необходим для создания проверок с атрибутами отношений
            )
    )
    result = session.execute(statement).scalars().all()
    print(result)
    print(f"\n[>] Списки записей {login} выведен!")

    return 0

def select_model(session, model, attribute : str, value):
    '''
        В текущей сессии ищем объект в выбранной модели и с определенным
        атрибутом
    '''
    model_attribute = getattr(model, attribute)
    statement = sql.select(model).where(
        model_attribute == value
    )
    result = session.execute(statement).first()
    return result

def delete_model(session, model, attribute, value):
    select = select_model(session, model, attribute, value)
    print(f"[>] У модели {model} была удалена запись: \n {select}")
    for record in select:
        session.delete(record)
        session.commit()
