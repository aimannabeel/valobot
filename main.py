import os
import aiohttp
import asyncio
from urllib.parse import quote
import discord
import ssl
import certifi
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
guildId = os.getenv("GUILD_ID")
HENRIK_API_KEY = os.getenv("HENRIK_API_KEY")
ssl_context = ssl.create_default_context(cafile=certifi.where())

MODE_LABELS = {
    "all": "All",
    "competitive": "Competitive",
    "unrated": "Unrated",
    "spikerush": "Spike Rush",
    "teamdeathmatch": "Team Deathmatch",
    "deathmatch": "Deathmatch",
    "swiftplay": "Swiftplay",
}

if token is None:
    raise ValueError("DISCORD_TOKEN is missing from .env")

if guildId  is None:
    raise ValueError("GUILD_ID is missing from .env")

if not HENRIK_API_KEY:
    raise ValueError("HENRIK_API_KEY is missing from .env")


TESTGUILD = [discord.Object(id=int(guildIds.strip())) for guildIds in guildId.split(",")]

intents =  discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for TESTGUILDS in TESTGUILD:
        synced_commands = await bot.tree.sync(guild=TESTGUILDS)
    print(f"Synced {len(synced_commands)} slash command(s).")

def build_match_table(matches_payload, player_puuid):
    match_rows = []
     
    for match in matches_payload["data"]:
        all_players = match["players"]
     
        matching_player = None
     
        for player in all_players:
            if player["puuid"] == player_puuid:
                matching_player = player
                break
        if matching_player is None:
            continue
     
        player_team_id = matching_player["team_id"]
     
        matching_team = None
     
        for team in match["teams"]:
            if team["team_id"] == player_team_id:
                matching_team = team
                break
     
        if matching_team is None:
            continue
     
        match_win_status = "🟩 Victory" if matching_team["won"] else "🟥 Defeat"
     
        map_name = match["metadata"]["map"]["name"]
        mode = match["metadata"]["queue"]["name"]
        agent_name = matching_player["agent"]["name"]
     
        stats = matching_player["stats"]
        kills = stats["kills"]
        deaths = stats["deaths"]
        assists = stats["assists"]
     
        row = f"**{match_win_status} • {map_name}**\n {agent_name} • {mode} • {kills}/{deaths}/{assists}"

        match_rows.append(row)

    if match_rows:
        return "\n\n".join(match_rows)
    else:
        return "No recent matches found."

def calculate_recent_stats(matches_payload, player_puuid):
    total_kills = 0
    total_deaths = 0
    total_headshots = 0
    total_bodyshots = 0
    total_legshots = 0
    matches_counted = 0

    

    for match in matches_payload["data"]:
        all_players = match["players"]
             
        matching_player = None
             
        for player in all_players:
            if player["puuid"] == player_puuid:
                matching_player = player
                break
            if matching_player is None:
                continue

        stats = matching_player["stats"]

        total_kills += stats["kills"]
        total_deaths += stats["deaths"]
        total_headshots += stats["headshots"]
        total_bodyshots += stats["bodyshots"]
        total_legshots += stats["legshots"]
        matches_counted += 1

    if matches_counted == 0:
        return "No recent stats found."

    kd = total_kills/total_deaths if total_deaths > 0 else total_kills

    total_shots = total_headshots + total_bodyshots + total_legshots
    hs_percent = (total_headshots/total_shots) * 100 if total_shots > 0 else 0

    return f"K/D: {kd:.2f} • HS: {hs_percent:.1f}%"
    


def build_match_url(region_value, safe_name, safe_tag, mode="all"):
    base_url = f"https://api.henrikdev.xyz/valorant/v4/matches/{region_value}/pc/{safe_name}/{safe_tag}"

    if mode == "all":
        return f"{base_url}?size=5"

    return f"{base_url}?size=5&mode={mode}"

class ModeSelect(discord.ui.Select):
    def __init__(self, player_name, player_tag, region, player_puuid, embed):

        self.player_name = player_name
        self.player_tag = player_tag
        self.region = region
        self.player_puuid = player_puuid
        self.embed = embed
        options = [
            discord.SelectOption(label="All", value="all"),
            discord.SelectOption(label="Competitive", value="competitive"),
            discord.SelectOption(label="Unrated", value="unrated"),
            discord.SelectOption(label="Spike Rush", value="spikerush"),
            discord.SelectOption(label="Team Deathmatch", value="teamdeathmatch"),
            discord.SelectOption(label="Deathmatch", value="deathmatch"),
            discord.SelectOption(label="Swiftplay", value="swiftplay"),
            ]

        super().__init__(
            placeholder="Choose match mode",
            min_values = 1,
            max_values = 1,
            options = options,
            )

    async def callback(self, interaction: discord.Interaction):
        selected_mode = self.values[0]

        safe_name = quote(self.player_name, safe ="")
        safe_tag = quote(self.player_tag, safe ="")

        matches_url = build_match_url(self.region.value, safe_name, safe_tag, selected_mode)

        headers = {"Authorization": HENRIK_API_KEY}
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector) as session:
                async with session.get(matches_url) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            f"Could not load {selected_mode} matches. Error {response.status}.",
                            ephemeral=True,
                        )
                        return
                    matches_payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) :
            await interaction.followup.send(
            "Could not reach the Valorant API. Please try again shortly.",
            ephemeral=True,
        )
            return
        mode_label = MODE_LABELS[selected_mode]

        self.embed.set_field_at(
            index = 4,
            name=f"Recent {mode_label} Matches",
            value=build_match_table(matches_payload, self.player_puuid),
            inline=False,
        )


        await interaction.message.edit(embed=self.embed, view=self.view)
                

        

class ModeView(discord.ui.View):
    def __init__(self, player_name, player_tag, region, player_puuid, embed):
        super().__init__(timeout=120)
        self.add_item(ModeSelect(player_name, player_tag, region, player_puuid, embed))


@bot.tree.command(
    name="valstats",
    description="Show a Valorant player's recent stats.",
)

@app_commands.guilds(*TESTGUILD)
@app_commands.choices(
    region= [app_commands.Choice(name="Asia Pacific", value="ap"),
             app_commands.Choice(name="North America", value="na"),
             app_commands.Choice(name="Europe", value="eu"),
             app_commands.Choice(name="Korea", value="kr"),
             app_commands.Choice(name="Latin America", value="latam"),
             app_commands.Choice(name="Brazil", value="br"),
        ]
)

async def valstat(interaction: discord.Interaction, name: str, tag: str, region: app_commands.Choice[str],):
    await interaction.response.defer(thinking=True)

    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region.value}/pc/{safe_name}/{safe_tag}"
    account_url = f"https://api.henrikdev.xyz/valorant/v1/account/{safe_name}/{safe_tag}"
    matches_url = build_match_url(region.value, safe_name, safe_tag)

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector,) as session:
            async with session.get(rank_url) as response:
                if response.status == 404:
                    await interaction.followup.send("Could not find this player. Check the name, tag and region.")
                    return
                if response.status != 200:
                    await interaction.followup.send(f"Valorant API returned error {response.status}. Try again shortly.")
                    return
                rank_payload = await response.json()
            async with session.get(account_url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"Found the player, but could not load their account level. Error {response.status}.")
                    return
                account_payload = await response.json()
            async with session.get(matches_url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"Found the player, but could not load their match history. Error {response.status}.")
                    return
                matches_payload = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        print(f"HenrikDev request failed: {type(error).__name__}: {error!r}")
        await interaction.followup.send("Could not reach the Valorant API. Please try again shortly")
        return

    
    rank_data = rank_payload["data"]               #all rank data
    account_data = account_payload["data"]         #all account data (level etc.)


    player_data = rank_data["account"]                        #self explanatory
    player_level = account_data["account_level"]
    player_puuid = player_data["puuid"]
    player_name = player_data["name"]
    player_tag = player_data["tag"]
    player_rank_info = rank_data["current"]
    player_rank = player_rank_info["tier"]["name"]
    player_peak_rank = rank_data["peak"]["tier"]["name"]
    player_rr = player_rank_info["rr"]

    embed = discord.Embed(
        title=f"{player_name}#{player_tag}",
        description= f"**Peak: {player_peak_rank}**",
        color= discord.Color.red(), )
    embed.add_field(
                name = "Level",
                value= f"{player_level}",
                inline = True,
            )
    embed.add_field(
        name="Rank",
        value=f"{player_rank}",
        inline=True,
    )
    embed.add_field(
        name="Current RR",
        value=f"{player_rr}",
        inline=True,
    )
    embed.add_field(
        name = "Recent Summary",
        value= calculate_recent_stats(matches_payload, player_puuid),
        inline = False,
            )
    embed.set_footer(text=f"{region.name} • PC")

    embed.add_field(
        name="All Recent Matches",
        value=build_match_table(matches_payload=matches_payload, player_puuid=player_puuid),
        inline=False,
    )
    await interaction.followup.send(embed=embed, view=ModeView(player_name, player_tag, region, player_puuid, embed))


bot.run(token=token)
