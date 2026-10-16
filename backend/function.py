import hashlib

def generated_hash(text):
    hash = hashlib.sha256()
    # объявляем объект хэш=функции с хэшированием методом sha256
    text_bytes = text.encode('utf-8')
    # конвертируем входящие значение в байтовый поток
    hash.update(text_bytes)
    # преобразовываем байтовый поток в хэш
    return hash.hexdigest() # возвращаем хэш в 16-ом виде

