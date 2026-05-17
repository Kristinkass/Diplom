# Система бронирования и управления рабочими местами в коворкинге

Веб-сайт для бронирования рабочих мест в коворкинге. Проект написан на Python с использованием Flask и базы данных MySQL.


Перед запуском проекта установите:

1. Python 3.10 или новее.
2. MySQL Server.
3. Git, если проект будет скачиваться из репозитория.
4. Любой редактор кода, например PyCharm или Visual Studio Code.

## Как развернуть проект

### Выполните команду:

```bash
git clone https://github.com/Kristinkass/Diplom

# Перейдите в папку проекта:
cd Diplom

# Создание и активация виртуального окружения
python -m venv venv

# Для Windows
venv\Scripts\activate

# Для macOS/Linux
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

## Настроить базу данных MySQL

Откройте MySQL и создайте базу данных:

```sql
CREATE DATABASE coworking_boo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
По умолчанию проект подключается к базе данных со следующими параметрами:
 
```text
host: localhost
port: 3306
user: root
password: 123456
database: coworking_boo
```
Если у вас другой пароль/пользователь MySQL, нужно указать свои данные в файле `.env`.
 
## Создать файл `.env`
 
В корне проекта создайте файл `.env` и вставьте туда:
 
```env
SECRET_KEY=dev-secret-key-change-in-production
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=123456
DB_NAME=coworking_boo
DB_PORT=3306
```
Если пароль/пользователь от MySQL другой, замените значение `DB_PASSWORD` и `DB_USER`.
 
## Запустить сайт

В папке проекта выполните:

```bash
python app.py
```

При первом запуске приложение автоматически создаст таблицы в базе данных и добавит тестовые данные.

Администратор:

```text
email: admin@coworking.com
password: 123456
```

Менеджер:

```text
email: manager@coworking.com
password: 123456
```

## Основные файлы проекта

- **`app.py`**: основной файл запуска сайта.
- **`models.py`**: модели базы данных и создание тестовых данных.
- **`config.py`**: настройки подключения к базе данных.
- **`requirements.txt`**: список Python-библиотек.
- **`templates/`**: HTML-шаблоны страниц.
- **`static/`**: стили, изображения и статические файлы.
