# Meme Battle

Браузерная мультиплеерная карточная игра, где игроки отвечают на ситуации мемами. Цель — избавиться от всех карт на руке быстрее остальных.

## Геймплей

Каждый раунд игрокам выпадает ситуация. Нужно выбрать подходящий мем из руки и сыграть его. Победителя раунда определяет ведущий (режим **Czar**) или голосование всех игроков (режим **No Czar**). Кто сыграл лучший мем — отдаёт карту. Проигравший получает штрафные карты. Побеждает тот, кто первым опустошает руку.

**Специальные карты:**
- `steal` — украсть карту у другого игрока
- `skip_penalty` — отменить штрафные карты в этом раунде
- `double_play` — сыграть два мема одновременно

**Категории ситуаций:** работа, учёба, отношения, интернет — или всё сразу.

## Стек

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.13, FastAPI, WebSocket, SQLAlchemy 2.0 async |
| База данных | PostgreSQL 16 |
| Кэш / pub-sub | Redis 7 |
| Frontend | React, Vite |
| Deploy | Docker Compose, Nginx |

## Запуск через Docker (рекомендуется)

```bash
cp .env.example .env
# Отредактируйте .env: замените SECRET_KEY на случайную строку

docker compose up --build
```

Приложение будет доступно на `http://localhost`.

## Локальная разработка

**Backend:**
```bash
cd backend
py -3.13 -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
node node_modules/vite/bin/vite.js
# или: npm run dev
```

**Тесты:**
```bash
cd backend
py -3.13 -m pytest tests/
```
99 тестов, покрыты все фазы раунда, авторизация, WebSocket-события.

## Переменные окружения

Скопируйте `.env.example` в `.env`:

```env
SECRET_KEY=change-me-to-a-long-random-string-in-production
DATABASE_URL=postgresql+asyncpg://meme:meme@db:5432/meme_battle
REDIS_URL=redis://redis:6379
```

## API

После запуска документация доступна по адресу `http://localhost:8000/docs`.

Основные группы эндпоинтов:

- `POST /api/auth/register` — регистрация
- `POST /api/auth/login` — вход, возвращает JWT
- `GET /api/auth/me` — текущий пользователь
- `POST /api/rooms` — создать комнату
- `GET /api/rooms` — список публичных комнат
- `POST /api/rooms/{code}/join` — войти по коду
- `WS /ws/{room_code}` — WebSocket соединение для игры
- `GET /api/stats/leaderboard` — таблица лидеров

## Структура проекта

```
Meme-Battle/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI приложение
│   │   ├── models.py        # SQLAlchemy модели
│   │   ├── routers/         # auth, rooms, stats, websocket
│   │   ├── game_engine.py   # логика раундов
│   │   └── connection_manager.py  # WebSocket менеджер
│   ├── tests/               # 99 async тестов
│   └── seed.py              # начальные данные (мемы, ситуации)
├── frontend/
│   └── src/
│       ├── pages/           # HomePage, LobbyPage, GamePage, ProfilePage
│       ├── components/      # MemeCard, PlayerList, Timer, ...
│       ├── context/         # Auth, Game, Theme
│       └── hooks/           # useGameSocket
├── docker-compose.yml
└── .env.example
```

## Деплой на сервер

```bash
py -3.13 deploy.py
```

Скрипт собирает образы, подключается к серверу и перезапускает `docker compose`.
