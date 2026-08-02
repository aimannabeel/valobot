import os
import aiohttp
import asyncio
from urllib.parse import quote
import discord
import sqlite3
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

DATABASE_NAME = "valobot.db"

def setup_db():
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_players(
        discord_user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        tag TEXT NOT NULL,
        region TEXT NOT NULL
    )
""")

    connection.commit()
    connection.close()

def save_player_id(discord_user_id, name, tag, region):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO saved_players (discord_user_id, name, tag, region)
        VALUES(?,?,?,?)

        ON CONFLICT(discord_user_id) DO UPDATE SET
            name = excluded.name,
            tag = excluded.tag,
            region = excluded.region
""", (discord_user_id, name, tag, region))

    connection.commit()
    connection.close()

def get_saved_player_id(discord_user_id):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT name, tag, region FROM saved_players WHERE discord_user_id = ?""",
        (discord_user_id,)
    )
    saved_player = cursor.fetchone()

    connection.close()

    return saved_player

def delete_player_id(discord_user_id):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    
    cursor.execute(
        """DELETE FROM saved_players WHERE discord_user_id = ?""", (discord_user_id,)
    )

    delete_count = cursor.rowcount

    connection.commit()
    connection.close()
    return delete_count

MODE_LABELS = {
    "all": "All",
    "competitive": "Competitive",
    "unrated": "Unrated",
    "spikerush": "Spike Rush",
    "teamdeathmatch": "Team Deathmatch",
    "deathmatch": "Deathmatch",
    "swiftplay": "Swiftplay",
}

REGION_LABELS = {
    "ap": "Asia Pacific",
    "na": "North America",
    "eu": "Europe",
    "kr": "Korea",
    "latam": "Latin America",
    "br": "Brazil",
}
RANK_VALUES = {
    "Unranked": 0,
    "Iron 1": 1,
    "Iron 2": 2,
    "Iron 3": 3,
    "Bronze 1": 4,
    "Bronze 2": 5,
    "Bronze 3": 6,
    "Silver 1": 7,
    "Silver 2": 8,
    "Silver 3": 9,
    "Gold 1": 10,
    "Gold 2": 11,
    "Gold 3": 12,
    "Platinum 1": 13,
    "Platinum 2": 14,
    "Platinum 3": 15,
    "Diamond 1": 16,
    "Diamond 2": 17,
    "Diamond 3": 18,
    "Ascendant 1": 19,
    "Ascendant 2": 20,
    "Ascendant 3": 21,
    "Immortal 1": 22,
    "Immortal 2": 23,
    "Immortal 3": 24,
    "Radiant": 25,
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

def calculate_recent_match_stats(matches_payload, player_puuid):
    total_kills = 0
    total_deaths = 0
    total_headshots = 0 
    total_bodyshots = 0
    total_legshots = 0
    wins = 0
    losses = 0
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

        player_team_id = matching_player["team_id"]

        matching_team = None

        for team in match["teams"]:
            if team["team_id"] == player_team_id:
                matching_team = team
                break

        if matching_team is None:
            continue

        if matching_team["won"]:
            wins+=1
        else:
            losses += 1

        stats = matching_player["stats"]
        total_kills += stats["kills"]
        total_deaths += stats["deaths"]
        total_headshots += stats["headshots"]
        total_bodyshots += stats["bodyshots"]
        total_legshots += stats["legshots"]
        matches_counted += 1

    if matches_counted == 0:
        return {
            "kd": 0,
            "hs_percent": 0,
            "wins": 0,
            "losses": 0,
            "matches_counted": 0,
    }    

    kd = total_kills / total_deaths if total_deaths > 0 else total_kills

    total_shots = total_headshots + total_bodyshots + total_legshots
    hs_percent = (total_headshots / total_shots) * 100 if total_shots > 0 else 0

    return {
        "kd": kd,
        "hs_percent": hs_percent,
        "wins": wins,
        "losses": losses,
        "matches_counted": matches_counted,
    }


def calculate_recent_rr_change(mmr_history_payload):
    history = mmr_history_payload["data"]["history"]

    recent_games = history[:5]

    total_rr_change = 0

    for game in recent_games:
        total_rr_change += game["last_change"]

    return total_rr_change
    


def build_match_url(region_value, safe_name, safe_tag, mode="all"):
    base_url = f"https://api.henrikdev.xyz/valorant/v4/matches/{region_value}/pc/{safe_name}/{safe_tag}"

    if mode == "all":
        return f"{base_url}?size=5"

    return f"{base_url}?size=5&mode={mode}"

async def fetch_compare_data(name, tag, region_value):
    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region_value}/pc/{safe_name}/{safe_tag}"
    matches_url = build_match_url(region_value, safe_name, safe_tag, "competitive")
    mmr_history_url = f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region_value}/pc/{safe_name}/{safe_tag}"

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector,) as session:
        async with session.get(rank_url) as response:
            if response.status != 200:
                return None
            rank_payload = await response.json()
        async with session.get(matches_url) as response:
            if response.status != 200:
                return None
            matches_payload = await response.json()
        async with session.get(mmr_history_url) as response:
            if response.status != 200:
                return None
            mmr_history_payload = await response.json()

    rank_data = rank_payload["data"]
    player_data = rank_data["account"]
    player_puuid = player_data["puuid"]

    player_rank_info = rank_data["current"]
    player_rank = player_rank_info["tier"]["name"]
    player_rr = player_rank_info["rr"]

    recent_match_stats = calculate_recent_match_stats(matches_payload, player_puuid)
    recent_rr_change = calculate_recent_rr_change(mmr_history_payload)

    return {
        "name": player_data["name"],
        "tag": player_data["tag"],
        "rank": player_rank,
        "rr": player_rr,
        "rr_change": recent_rr_change,
        "kd": recent_match_stats["kd"],
        "hs_percent": recent_match_stats["hs_percent"],
        "wins": recent_match_stats["wins"],
        "losses": recent_match_stats["losses"],
        "matches_counted": recent_match_stats["matches_counted"],
    }

def build_compare_verdict(player1, player2, user1, user2):
    player1_score = 0
    player2_score = 0

    player1_rank = RANK_VALUES.get(player1["rank"], 0)
    player2_rank = RANK_VALUES.get(player2["rank"], 0)

    if player1_rank > player2_rank:
        player1_score += 1
    elif player2_rank > player1_rank:
        player2_score += 1
    if player1["kd"] > player2["kd"]:
        player1_score += 1
    elif player2["kd"] > player1["kd"]:
        player2_score += 1

    if player1["hs_percent"] > player2["hs_percent"]:
        player1_score += 1
    elif player2["hs_percent"] > player1["hs_percent"]:
        player2_score += 1

    if player1["wins"] > player2["wins"]:
        player1_score += 1
    elif player2["wins"] > player1["wins"]:
        player2_score += 1

    if player1["rr_change"] > player2["rr_change"]:
        player1_score += 1
    elif player2["rr_change"] > player1["rr_change"]:
        player2_score += 1

    if player1_score > player2_score:
        return f"Someone check {user1.mention}'s aimlabs hours. get rekt {user2.mention}"

    if player2_score > player1_score:
        return f"{user2.mention} ez win get clapped {user1.mention}. "

    return "This one is too close to call. Run it back and settle it in ranked."


    

class ModeSelect(discord.ui.Select):
    def __init__(self, player_name, player_tag, region_value, region_name, player_puuid, embed):

        self.player_name = player_name
        self.player_tag = player_tag
        self.region_value = region_value
        self.region_name = region_name
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

        matches_url = build_match_url(self.region_value, safe_name, safe_tag, selected_mode)

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
            index = 3,
            name=f"{mode_label} Summary",
            value= calculate_recent_stats(matches_payload, self.player_puuid),
            inline = False
        )

        self.embed.set_field_at(
            index = 4,
            name=f"Recent {mode_label} Matches",
            value=build_match_table(matches_payload, self.player_puuid),
            inline=False,
        )


        await interaction.message.edit(embed=self.embed, view=self.view)
                

        

class ModeView(discord.ui.View):
    def __init__(self, player_name, player_tag, region_value, region_name, player_puuid, embed):
        super().__init__(timeout=120)
        self.add_item(ModeSelect(player_name, player_tag, region_value, region_name, player_puuid, embed))

async def send_valstats(interaction, name, tag, region_value, region_name):
    await interaction.response.defer(thinking=True)

    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region_value}/pc/{safe_name}/{safe_tag}"
    account_url = f"https://api.henrikdev.xyz/valorant/v1/account/{safe_name}/{safe_tag}"
    matches_url = build_match_url(region_value, safe_name, safe_tag)
    mmr_history_url = f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region_value}/pc/{safe_name}/{safe_tag}"

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
            async with session.get(mmr_history_url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"Found the player, but could not load their RR history. Error {response.status}.")
                    return
                mmr_history_payload = await response.json()

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
    recent_rr_change = calculate_recent_rr_change(mmr_history_payload)

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
        value=f"{player_rr} ({recent_rr_change:+})",
        inline=True,
    )
    embed.add_field(
        name = "Recent Summary",
        value= calculate_recent_stats(matches_payload, player_puuid),
        inline = False,
            )
    embed.set_footer(text=f"{region_name} • PC")

    embed.add_field(
        name="All Recent Matches",
        value=build_match_table(matches_payload=matches_payload, player_puuid=player_puuid),
        inline=False,
    )
    await interaction.followup.send(embed=embed, view=ModeView(player_name, player_tag, region_value, region_name, player_puuid, embed))

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
    await send_valstats(interaction, name, tag, region.value, region.name)

@bot.tree.command(
    name="setid",
    description="Save your valorant ID for quick stat lookups."
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
async def setid(
    interaction: discord.Interaction,
    name:str,
    tag: str,
    region: app_commands.Choice[str]
):
    discord_user_id = str(interaction.user.id)

    save_player_id(discord_user_id, name, tag, region.value)

    await interaction.response.send_message(f"Set your Valorant ID **{name}#{tag}** in **{region.name}**.", ephemeral=True)

@bot.tree.command(
    name="myid",
    description="View your saved Valorant ID"
)

@app_commands.guilds(*TESTGUILD)
async def myid(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)

    saved_player = get_saved_player_id(discord_user_id)

    if saved_player == None:
        await interaction.response.send_message("You do not have a saved Valorant ID yet. Use '/setid' first.", ephemeral=True)
        return

    name, tag, region = saved_player

    region_label = REGION_LABELS[region]

    await interaction.response.send_message(f"Your saved Valorant ID is **{name}#{tag}** in region **{region_label}**", ephemeral=True)

@bot.tree.command(
    name="unsetid",
    description="Remove your saved Valorant ID"
)
@app_commands.guilds(*TESTGUILD)
async def unsetid(interaction: discord.Interaction):
    saved_player_id = str(interaction.user.id)

    deleted_count = delete_player_id(saved_player_id)

    if deleted_count ==0:
        await interaction.response.send_message("You do not have a saved Valorant ID to remove.", ephemeral = True,)
        return

    await interaction.response.send_message("Removed you saved valorant ID.", ephemeral = True)

@bot.tree.command(
    name="valstatsme",
    description="Show stats for your saved Valorant ID."
)
@app_commands.guilds(*TESTGUILD)
async def valstatsme(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)

    saved_player = get_saved_player_id(discord_user_id)

    if saved_player is None:
        await interaction.response.send_message(
            "You do not have a saved Valorant ID yet. Use `/setid` first.",
            ephemeral=True,
        )
        return

    name, tag, region = saved_player
    region_name = REGION_LABELS[region]

    await send_valstats(interaction, name, tag, region, region_name)

@bot.tree.command(
    name = "valstatsuser",
    description="Show stats for Discord user's if they have linked Valorant ID."
)
@app_commands.guilds(*TESTGUILD)
async def valstatuser(interaction: discord.Interaction, user: discord.User):
    discord_user_id = str(user.id)

    saved_player = get_saved_player_id(discord_user_id)

    if saved_player is None:
        await interaction.response.send_message(
            f"{user.mention} does not have a linked Valorant ID yet.",
            ephemeral=True
        )
        return

    name, tag, region = saved_player
    region_name = REGION_LABELS[region]

    await send_valstats(interaction, name, tag, region, region_name)

@bot.tree.command(
    name = "help",
    description="Show all Valobot commands."
)

@app_commands.guilds(*TESTGUILD)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Valobot Commands",
        description="Quick guide to the available commands.",
        color=discord.Color.red(),
    )
    
    embed.add_field(
        name="/valstatsme",
        value="Show stats using your linked Valorant ID.",
        inline=False,
    )

    embed.add_field(
        name="/valstatsuser",
        value="Show stats for another Discord user's linked Valorant ID.",
        inline=False,
    )

    embed.add_field(
        name="/valstats",
        value="Look up a Valorant player using name, tag, and region.",
        inline=False,
    )
    
    embed.add_field(
        name="/setid",
        value="Link your Discord account with your Valorant ID.",
        inline=False,
    )

    embed.add_field(
        name="/myid",
        value="Show your linked Valorant ID.",
        inline=False,
    )

    embed.add_field(
        name="/unsetid",
        value="Remove your linked Valorant ID.",
        inline=False,
    )

    embed.add_field(
    name="/compare",
    value="Compare two linked Valorant players using recent competitive stats.",
    inline=False,
)

    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(
    name = "compare",
    description  = "Compare two linked Valorant players."
)

@app_commands.guilds(*TESTGUILD)
async def compare(interaction: discord.Interaction, user1: discord.User, user2: discord.User):
    await interaction.response.defer(thinking=True)

    saved_player1 = get_saved_player_id(str(user1.id))
    saved_player2 = get_saved_player_id(str(user2.id))

    if saved_player1 is None:
        await interaction.followup.send(
            f"{user1.mention} has not linked a Valorant ID yet. Ask them to use `/setid` first.",
            ephemeral=True,
        )
        return

    if saved_player2 is None:
        await interaction.followup.send(
            f"{user2.mention} has not linked a Valorant ID yet. Ask them to use `/setid` first.",
            ephemeral=True,
        )
        return

    name1, tag1, region1 = saved_player1
    name2, tag2, region2 = saved_player2

    player1 = await fetch_compare_data(name1, tag1, region1)
    player2 = await fetch_compare_data(name2, tag2, region2)

    if player1 is None or player2 is None:
        await interaction.followup.send(
            "Could not load compare stats. Try again shortly.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"{player1['name']}#{player1['tag']} vs {player2['name']}#{player2['tag']}",
        description="Based on each player's last 5 competitive matches.",
        color=discord.Color.red(),
    )

    embed.add_field(
        name ="Rank",
        value =f"{player1['rank']} vs {player2['rank']}",
        inline = False
    )

    embed.add_field(
        name = "Recent RR Change",
        value = f"{player1['rr_change']:+} vs {player2['rr_change']:+}",
        inline = False
    )

    embed.add_field(
            name ="Recent Record",
            value =f"{player1['wins']}W-{player1['losses']}L vs {player2['wins']}W-{player2['losses']}L",
            inline = False
        )

    embed.add_field(
        name="Recent K/D",
        value=f"{player1['kd']:.2f} vs {player2['kd']:.2f}",
        inline=False,
    )

    embed.add_field(
        name="Headshot %",
        value=f"{player1['hs_percent']:.1f}% vs {player2['hs_percent']:.1f}%",
        inline=False,
    )

    embed.add_field(
        name="Verdict",
        value=build_compare_verdict(player1, player2, user1, user2),
        inline=False,
    )

    await interaction.followup.send(embed=embed)

    


setup_db()
bot.run(token=token)
