# Система управления рабочими местами в коворкинге

Веб-приложение для бронирования рабочих мест и переговорных.

**Стек:** Python 3.10+, Flask, PostgreSQL, SQLAlchemy. Геометрия этажей — в `static/layout.json`, бизнес-данные — в PostgreSQL.

## Требования

- Python 3.10+
- PostgreSQL 12+
- Git

## Быстрый старт (локально)

```bash
git clone <url-репозитория>
cd <папка-проекта>

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Скопируйте `.env.example` в `.env` и укажите параметры подключения к БД:

```env
SECRET_KEY=ваша_случайная_строка
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=ваш_пароль
DB_NAME=coworking
DB_PORT=5432

ADMIN_EMAIL=admin@coworking.com
ADMIN_PASSWORD=ВашНадёжныйПароль
ADMIN_NAME=Администратор
```

Запуск в режиме разработки:

```bash
python cmd/app/main.py
```

Приложение: http://127.0.0.1:5000

При первом запуске создаются таблицы, выполняются миграции и инициализируются начальные данные (включая администратора из `.env`).

## API-документация (Swagger)

После запуска доступны:

| URL | Описание |
|-----|----------|
| http://127.0.0.1:5000/docs/ | Swagger UI |
| http://127.0.0.1:5000/openapi.json | OpenAPI 3.0 спецификация |

Документация генерируется автоматически из всех зарегистрированных маршрутов Flask. Для защищённых эндпоинтов используется сессионная cookie (`session`) — сначала войдите через `/login`.

## Запуск через Docker

```bash
# Скопируйте и настройте переменные
cp .env.example .env

# Сборка и запуск (приложение + PostgreSQL)
docker compose up --build
```

Приложение: http://localhost:5000  
Swagger: http://localhost:5000/docs/

Остановка:

```bash
docker compose down
```

Данные PostgreSQL сохраняются в Docker volume `pgdata`.

## Структура проекта

```text
cmd/app/main.py          — точка входа (dev)
wsgi.py                  — точка входа (production / Docker)
internal/
  application.py         — фабрика Flask
  config.py              — настройки
  swagger/               — OpenAPI / Swagger UI
  handlers/              — HTTP-маршруты
  services/              — бизнес-логика
  repositories/          — доступ к PostgreSQL
  layout/                — карта (layout.json)
  models/                — ORM и миграции
static/                  — CSS, JS, layout.json
templates/               — HTML-шаблоны
Dockerfile
docker-compose.yml
```

## Production (без Docker)

```bash
pip install -r requirements.txt
# задайте переменные окружения или .env
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```
