import os
import aiohttp
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
HENRICK_API_KEY = os.getenv("HENRICK_API_KEY")
ssl_context = ssl.create_default_context(cafile=certifi.where())

if token is None:
    raise ValueError("DISCORD_TOKEN is missing from .env")

if guildId  is None:
    raise ValueError("GUILD_ID is missing from .env")

if not HENRICK_API_KEY:
    raise ValueError("HENRICK_API_KEY is missing from .env")


TESTGUILD = discord.Object(id=int(guildId))

intents =  discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    synced_commands = await bot.tree.sync(guild=TESTGUILD)
    print(f"Logged in as {bot.user}")
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
     
        match_win_status = "W" if matching_team["won"] else "L"
     
        map_name = match["metadata"]["map"]["name"]
        mode = match["metadata"]["queue"]["name"]
        agent_name = matching_player["agent"]["name"]
     
        stats = matching_player["stats"]
        kills = stats["kills"]
        deaths = stats["deaths"]
        assists = stats["assists"]
     
        row = f"{match_win_status:<2} {map_name[:10]:<10} {mode[:11]:<11} {agent_name[:9]:<9} {kills}/{deaths}/{assists}"
        match_rows.append(row)

    table_header = f"{'R':<2} {'Map':<10} {'Mode':<11} {'Agent':<9} KDA"

    if match_rows:
        match_table = "\n".join(match_rows)
    else:
        match_table = "No recent matches found."

    return f"```{table_header}\n{match_table}```"

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

        if selected_mode == "all":
            matches_url = f"https://api.henrikdev.xyz/valorant/v4/matches/{self.region.value}/pc/{safe_name}/{safe_tag}?size=5"
        else:
            matches_url =f"https://api.henrikdev.xyz/valorant/v4/matches/{self.region.value}/pc/{safe_name}/{safe_tag}?size=5&mode={selected_mode}"

        headers = {"Authorization": HENRICK_API_KEY}
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
        except aiohttp.ClientError:
            await interaction.followup.send(
            "I could not reach the Valorant API. Please try again shortly.",
            ephemeral=True,
        )
            return

        self.embed.set_field_at(index = 3,name=f"Recent Matches: {selected_mode.title()}", value=build_match_table(matches_payload, self.player_puuid), inline=False,)
        await interaction.message.edit(embed=self.embed, view=self.view)
                

        

class ModeView(discord.ui.View):
    def __init__(self, player_name, player_tag, region, player_puuid, embed):
        super().__init__(timeout=120)
        self.add_item(ModeSelect(player_name, player_tag, region, player_puuid, embed))


@bot.tree.command(
    name="valstats",
    description="Show a Valorant player's recent stats.",
)

@app_commands.guilds(TESTGUILD)
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
    matches_url = f"https://api.henrikdev.xyz/valorant/v4/matches/{region.value}/pc/{safe_name}/{safe_tag}?size=5"

    headers = {"Authorization": HENRICK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector,) as session:
            async with session.get(rank_url) as response:
                if response.status == 404:
                    await interaction.followup.send("I could not find this player, try using region")
                    return
                if response.status != 200:
                    await interaction.followup.send(f"Valorant API returned error {response.status}. Try again shortly")
                    return
                rank_payload = await response.json()
            async with session.get(account_url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"I found the player's, but could not load their account level. Error {response.status}.")
                    return
                account_payload = await response.json()
            async with session.get(matches_url) as response:
                            if response.status != 200:
                                await interaction.followup.send(f"I found the player's, but could not load their match history. Error {response.status}.")
                                return
                            matches_payload = await response.json()
    except aiohttp.ClientError as error:
        print(f"HenrikDev request failed: {type(error).__name__}: {error!r}")
        await interaction.followup.send("I could not reach the Valorant API. Please try again shortly")
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
    player_rr = player_rank_info["rr"]

    embed = discord.Embed(
        title=f"{player_name}#{player_tag}",
        description= "Current Rank and info",
        color= discord.Color.red(), )
    embed.add_field(
        name = "Rank",
        value= f"{player_rank}",
        inline = False,
    )
    embed.add_field(
            name = "Current RR",
            value= f"{player_rr}",
            inline = False,
        )
    embed.add_field(
                name = "Level",
                value= f"{player_level}",
                inline = False,
            )
    embed.set_footer(text=f"{region.name} • PC")

    embed.add_field(
        name="Recent Matches",
        value=build_match_table(matches_payload=matches_payload, player_puuid=player_puuid),
        inline=False,
    )
    await interaction.followup.send(embed=embed, view=ModeView(player_name, player_tag, region, player_puuid, embed))


bot.run(token=token)
