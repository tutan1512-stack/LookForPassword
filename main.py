import backend.model as m
import backend.function as f
import backend.orm_function as orm
import sqlalchemy as sql

runApp = True
app = ("\n<< Менеджер записей >>\n1. Создать аккаунт\n2. Войти в аккаунт"
       "\n0. Выйти из приложения\n\n[<] Введите действие: ")



while runApp == True:
    answer = input(app)
    match answer:
        case "1":
            login_v = input('\n[<] Введите логин: ')
            password_v = input('[<] Введите пароль: ')
            with orm.session_orm() as s:

                orm.no_duplicate(s, login_v, password_v)

                statement = sql.select(m.User)
                #  оборачиваем селект в переменную
                s.commit()
                # передаем наш запрос на базу данных для выполнения (execute)
                print(s.execute(statement).scalars().all())

        case "2":
            login_v = input('\n[<] Введите логин: ')
            password_v = input('[<] Введите пароль: ')
            with orm.session_orm() as s:
                flag = orm.comparison(s, login_v, password_v)

                if flag == True:
                    runAccount = True
                    while runAccount:
                        answer_account = input(f"\n Добро пожаловать {login_v}! \n\n"
                              f"1. Создать пост\n2. Прочитать  пост\n3. Изменить пост\n4. Удалить пост"
                              f"\n0. Выйти из аккаунта\n\n[<] Введите действие: ")
                        match answer_account:
                            case "1":

                                orm.create_post(s, login_v)

                                s.commit()

                            case "2":
                                pass

                            case "3":
                                pass

                            case "4":
                                pass

                            case "0":
                                runAccount = False
                                print(f"\nПрощайте, {login_v}!\n")
                                s.rollback()

        case "0":
            runApp = False




