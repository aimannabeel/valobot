# Valobot

Valobot is a custom Discord bot for viewing Valorant player stats directly inside a Discord server.

I am building this project in phases while learning Python, Discord bots, APIs, Git, and GitHub. The first goal is to make a solid `/valstats` command before adding bigger features like saved player IDs, leaderboards, shop lookup, and AI commands.

## Features

- `/valstats` slash command
- Shows Valorant player level
- Shows current rank, peak rank, and RR
- Shows recent match history
- Shows recent K/D and headshot percentage calculated from the last 5 matches
- Displays map, mode, agent, KDA, and win/loss result
- Dropdown menu for filtering match history by game mode
- `/setid` command to link your Discord account with your Valorant ID
- `/myid` command to view your linked Valorant ID
- `/unsetid` command to unlink your saved Valorant ID from your Discord account
- `/valstatsme` command to look up stats using your linked Valorant ID
- `/valstatsuser` command to look up another Discord user's linked Valorant ID
- `/compare` command to compare two linked players using recent competitive stats
- `/help` command to show available bot commands
- Shows recent RR gain/loss from competitive matches
- Uses SQLite for local saved-player storage
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

## Commands

| Command | Description |
| --- | --- |
| `/valstats` | Look up a Valorant player's stats using name, tag, and region |
| `/setid` | Link your Discord account Valorant ID for quicker lookups |
| `/myid` | Show your linked Valorant ID |
| `/unsetid` | Remove your linked Valorant ID |
| `/valstatsme` | Look up your stats using your linked Valorant ID |
| `/valstatsuser` | Look up another Discord user's stats if they linked their Valorant ID |
| `/compare` | Compare two linked Valorant players using recent competitive rank, RR change, record, K/D, and headshot percentage |
| `/help` | Show a quick guide to Valobot commands |

## Tech Stack

- Python
- discord.py
- aiohttp
- python-dotenv
- SQLite
- HenrikDev Valorant API
- Oracle Cloud VPS
- systemd
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
```

The bot also creates a local SQLite database file:

```text
valobot.db
```
This file stores saved Valorant IDs and is ignored by Git.

Run the bot:

```powershell

python main.py
```
## Deployment

The production bot is deployed on an Oracle Cloud VPS and runs as a `systemd` service.

Currently, Valobot is tested in private Discord servers while features are still being developed.

## Environment Variables

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Your Discord bot token |
| `HENRIK_API_KEY` | Your HenrikDev Valorant API key |

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

- [x] Save a Discord user's Valorant ID
- [x] Store saved IDs locally with SQLite
- [x] Add `/setid` command
- [x] Add `/myid` command
- [x] Add `/unsetid` command
- [x] Add `/valstatsme` command for checking saved stats
- [x] Add `/valstatsuser` command for checking another user's saved stats
- [x] Show how much RR gained or lost in the last 5 games
- [x] Add `/help` command
- [x] Add `/compare` command for comparing two players
- [x] Deploy the bot on Oracle Cloud VPS

### Phase 2: Add-On Features

- [ ] Add server leaderboard
- [ ] Add daily shop lookup

### Phase 3: AI Features

- [ ] Use match stats as context for AI responses or something (not sure)

### Future Polish

- [ ] Add custom image stat cards
- [ ] Add rank, agent, and map icons

## Notes

This project is currently in active development.

The `.env` file is intentionally ignored by Git so private tokens and API keys are not uploaded to GitHub.