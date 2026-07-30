# Valobot

Valobot is a custom Discord bot for viewing Valorant player stats directly inside a Discord server.

I am building this project in phases while learning Python, Discord bots, APIs, Git, and GitHub. The first goal is to make a solid `/valstats` command before adding bigger features like saved player IDs, leaderboards, shop lookup, and AI commands.

## Features

- `/valstats` slash command
- Shows Valorant player level
- Shows current rank and RR
- Shows recent match history
- Displays map, mode, agent, KDA, and win/loss result
- Dropdown menu for filtering match history by game mode
- Uses Discord embeds for clean responses
- Stores private tokens safely in a `.env` file which git ignores

## Match Filters

The match history dropdown currently supports:

- All
- Competitive
- Unrated
- Spike Rush
- Team Deathmatch
- Deathmatch
- Swiftplay

## Tech Stack

- Python
- discord.py
- aiohttp
- python-dotenv
- HenrikDev Valorant API
- Git
- GitHub

## Setup

Clone the repository:

```powershell
git clone https://github.com/aimannabeel/valobot.git
cd valobot
```

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```env
DISCORD_TOKEN=your_discord_bot_token
HENRIK_API_KEY=your_henrik_api_key
GUILD_ID=your_test_server_id
```

Run the bot:

```powershell
python main.py
```

## Environment Variables

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Your Discord bot token |
| `HENRIK_API_KEY` | Your HenrikDev Valorant API key |
| `GUILD_ID` | Discord server ID used for slash command testing |

## Project Roadmap

### Phase 1: Core Stats

- [x] Set up Python project
- [x] Set up Git and GitHub
- [x] Create basic Discord bot
- [x] Add `/valstats` slash command
- [x] Fetch Valorant rank and RR
- [x] Fetch player level
- [x] Fetch recent match history
- [x] Show map, mode, agent, KDA, and win/loss result
- [x] Add match mode dropdown
- [x] Improve match display formatting
- [x] Test bot in a friend's Discord server
- [x] Clean up error handling
- [x] Add recent K/D calculation
- [x] Add recent headshot percentage
- [x] Add peak rank if available from the API

### Phase 1.5: Saved Player IDs

- [ ] Save a Discord user's Valorant ID
- [ ] Add shortcut command for checking saved stats
- [ ] Store saved IDs safely in a local file or database
- [ ] Add `/compare` command for comparing two players

### Phase 2: Add-On Features

- [ ] Add server leaderboard
- [ ] Add daily shop lookup

### Phase 3: AI Features

- [ ] Use match stats as context for AI responses

### Future Polish

- [ ] Add custom image stat cards
- [ ] Add rank, agent, and map icons
- [ ] Deploy the bot so it can run 24/7

## Notes

This project is currently in active development.

The `.env` file is intentionally ignored by Git so private tokens and API keys are not uploaded to GitHub.