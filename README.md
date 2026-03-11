# tele-bot-test

<!-- cspell:words venv -->

## Project Goal

This project is designed to build a Telegram bot that we answer three different questions like (how are you,how old are you , where are you from) and storing the answers in sqlite database with the username who ask

## Tech Stack / Dependencies

- aiogram
- aiosqlite
- python-dotenv
- loguru
- apscheduler
- httpx
- ruff

## Important Team Rules

- Commit requirements.txt
- Do **not** commit venv/
- Keep venv/ in .gitignore
- Keep secrets in .env
- Do **not** commit real bot tokens or secrets
- Share .env.example as a safe template

## Project Setup (Windows)

### 1) Clone repository

`Bash
git clone <your-repo-url>
cd tele-bot-hk
`

### 2) Create virtual environment

`Bash
python -m venv venv
`

### 3) Activate virtual environment

- PowerShell:

`powershell
venv\Scripts\Activate.ps1
`

- CMD:

`cmd
venv\Scripts\activate.bat
`

> You need to activate it once per terminal session (or configure VS Code interpreter for auto-activation).

### 4) Install dependencies

`Bash
python -m pip install -r requirements.txt
`

### 5) Configure environment variables

Copy .env.example to .env and fill real values:

`Bash
copy .env.example .env
`

Then set your real BOT_TOKEN in .env.

### 6) Run the bot

`Bash
python main.py
`

## How to Verify venv is Active

Use either check:

`Bash
where python
python -m pip -V
`

Both paths should point to your project Venv directory. Prompt may also show (venv).
