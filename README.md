# Telegram Forwarding Bot - Developer Documentation

## 1) Project Overview

This project is a Telegram forwarding bot (aiogram + SQLite) that copies messages from source chats/channels/topics to destination chats/channels/topics with route-based control.

Core capabilities:

- Immediate message copy forwarding.
- Topic-aware routing (`source_topic_id` -> `destination_topic_id`).
- Edit synchronization from source to destination copies.
- Delete synchronization using Telethon (MTProto) listener.
- Role-based route management (owner + route managers).

---

## 2) Runtime Flow

1. Bot starts, reads settings from `.env`, initializes DB/migrations, and syncs route managers from env into DB.
2. Aiogram handlers listen to new/edited messages and channel posts.
3. New source messages are matched against active routes and copied immediately.
4. Edited source messages try inline edit first, then fallback to replace-copy when needed.
5. Telethon listener (optional) watches source deletes and removes mapped destination copies.

---

## 3) Roles and Permissions

- **Owner (`OWNER_ID`)**: can add/list/remove any route and run `/remove_all_routes`.
- **Route Manager (`ROUTE_MANAGER_IDS`)**: can add routes, list only own routes, and remove only own routes.
- **Unauthorized users**: cannot manage routes.

---

## 4) Environment Values Required to Run Well

Use `.env` copied from `.env.example`.

Required:

- `BOT_TOKEN` = Telegram bot token from @BotFather.
- `OWNER_ID` = Telegram numeric user id of project owner.

Recommended:

- `DATABASE_URL=sqlite:///bot.db`
- `LOG_LEVEL=INFO`
- `ROUTE_MANAGER_IDS=` comma-separated manager user ids (optional, leave empty if not needed).

Optional for delete-sync listener (Telethon/MTProto):

- `TELETHON_API_ID` = API id from my.telegram.org.
- `TELETHON_API_HASH` = API hash from my.telegram.org.
- `TELETHON_SESSION=telethon_session` = local user session name.

Telethon first-run note:

- On first run only, Telegram will ask for a verification code sent to that user account.
- After successful login, Telethon saves the local session file, so next runs normally do not ask again unless the session is removed/expired.
- `TELETHON_WATCH_CHAT_IDS=` = optional comma-separated source chat filter for delete events.

---

## 5) Operational Rules / Prerequisites

- Bot must be admin in all source and destination chats/channels it needs to read/write in.
- In channels, bot must be admin with permission to access posts.
- For delete-sync, you must provide a real Telegram user account API/session (Telethon) to receive delete events.
- Topic routing uses Telegram `message_thread_id` values.
- **The General Id in groups with topics is always 0.**
- In this project, topic value `0` is normalized as “general/no specific topic route” in database logic.

---

## 6) Bot Commands (Telegram)

Available to owner + managers (except where noted):

- `/start` -> show usage/help.
- `/chat_id` -> show current `chat_id`, chat type, and topic id (`message_thread_id`).
- `/add_route <source_chat_id> <destination_chat_id>` -> add chat-level route.
- `/add_route <source_chat_id> <destination_chat_id> <source_topic_id> <destination_topic_id>` -> add topic-aware route.
- `/list_routes` -> owner sees all; manager sees only own routes.
- `/remove_route <route_id>` -> owner removes any; manager removes only own.
- `/remove_all_routes` -> owner only.

---

## 7) Developer/Operations Commands

Setup and run:

```bash
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python main.py
```

Validation / maintenance:

```bash
python -m compileall bot main.py
python -m ruff check .
python -m pip freeze > requirements.txt
```

---

## 8) File Responsibilities (one line each)

- `main.py` - Application entrypoint that initializes DB/settings and starts aiogram + Telethon tasks.
- `bot/config.py` - Loads `.env`, validates configuration, and exposes typed runtime settings.
- `bot/database/db.py` - Defines schema, migrations, route CRUD logic, mapping tables, and permission helpers.
- `bot/handlers/commands.py` - Handles owner/manager Telegram commands for route management and diagnostics.
- `bot/handlers/messages.py` - Handles new and edited Telegram updates and forwards them to service layer.
- `bot/services/forwarder.py` - Executes copy forwarding, edit sync, delete sync, and logging per route.
- `bot/services/mtproto_listener.py` - Runs optional Telethon listener for source delete events.
- `bot/services/processor.py` - Contains legacy/simple QA text processing helpers not used in forwarding flow.
- `.env.example` - Safe template for required and optional environment values.
- `README.md` - Main project and developer documentation.
- `requirements.txt` - Python dependency lock list used to install runtime packages.
- `.gitignore` - Rules for excluding local artifacts/secrets from version control.
- `CLOSE_GUIDE.md` - Project-specific close/finish checklist document.
- `MERGE_GUIDE.md` - Project-specific merge workflow guidance.
- `doc.txt` - Additional project notes.

---

## 9) Database Tables Summary

- `routes` - Stores routing rules, topic mapping, owner/creator, and last-forwarded signature.
- `route_managers` - Stores active manager IDs synced from `.env`.
- `message_cache` - Stores recent source message IDs for local tracking.
- `forward_logs` - Stores forward/edit operation success/failure logs.
- `message_links` - Stores source->destination message mapping for edit/delete synchronization.

---

## 10) Notes for Future Developers

- Keep migrations backward-compatible because existing production DBs may have older constraints.
- Prefer additive schema evolution and explicit normalization (example: topic `0` handling).
- Validate with `compileall` + `ruff` before shipping changes.
- Keep secrets only in `.env`, never commit real credentials or session secrets.
