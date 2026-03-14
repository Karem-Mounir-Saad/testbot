# tele-bot-test

## Project Goal

This project is a Telegram forwarding bot built with aiogram.

The bot listens to updates from configured source chats/channels and forwards each new incoming message automatically to destination chats/channels.

Supported routing scenarios:

- Group ➜ Group
- Channel ➜ Channel
- Channel ➜ Group

---

## How the Workflow Works

1. Bot owner configures routes via commands in private chat with the bot.
2. Bot listens to incoming updates in source chats/channels.
3. For each new message/post in a configured source:
   - message ID is cached in SQLite (`message_cache`)
   - cache is trimmed to keep recent history
4. Bot forwards the incoming message immediately to each active destination route.
5. Cache is kept trimmed to preserve recent message history.
6. Forward results are tracked in `forward_logs` for observability and debugging.

To prevent duplicate forwarding, each route stores the last forwarded signature of message IDs.

---

## Tech Stack / Dependencies

- aiogram
- aiosqlite
- python-dotenv
- loguru
- apscheduler (reserved for future scheduled mode)
- httpx
- ruff

---

## Permission Requirements

The bot must be admin in **all source and destination** chats/channels.

- In groups/supergroups: bot should be able to receive messages.
- In channels: bot should be admin with access to channel posts.
- Destination chats/channels must allow bot posting/forwarding.

---

## Environment Variables

Use `.env` (copied from `.env.example`):

- `BOT_TOKEN` — token from @BotFather
- `OWNER_ID` — Telegram numeric user ID allowed to manage routes
- `DATABASE_URL` — SQLite URL, e.g. `sqlite:///bot.db`
- `LOG_LEVEL` — e.g. `INFO`

---

## Owner Commands

Use these in private chat with the bot:

- `/start`
  - shows usage/help

- `/add_route <source_chat_id> <destination_chat_id>`
  - adds or re-activates a route

- `/list_routes`
  - lists configured routes

- `/remove_route <route_id>`
  - deletes route by id

---

## Database Tables

- `routes`
  - route configuration
  - last forwarded signature per route

- `message_cache`
  - cached source message IDs

- `forward_logs`
  - success/failure logs for forwarding attempts

---

## Setup (Windows)

### 1) Clone repository

```bash
git clone <your-repo-url>
cd tele-bot-test
```

### 2) Create virtual environment

```bash
python -m venv venv
```

### 3) Activate virtual environment

- PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

- CMD:

```cmd
venv\Scripts\activate.bat
```

### 4) Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5) Configure env

```bash
copy .env.example .env
```

Then set real values for `BOT_TOKEN` and `OWNER_ID`.

### 6) Run bot

```bash
python main.py
```

---

## Team Rules

- Commit `requirements.txt`
- Do **not** commit `venv/`
- Keep secrets only in `.env`
- Do **not** commit real tokens/secrets
- Keep `.env.example` as safe template
