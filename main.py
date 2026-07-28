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
                    await interaction.followup.send(f"I found the player's rank, but could not load their account level. Error {response.status}.")
                    return
                account_payload = await response.json()
    except aiohttp.ClientError as error:
        print(f"HenrikDev request failed: {type(error).__name__}: {error!r}")
        await interaction.followup.send("I could not reach the Valorant API. Please try again shortly")
        return
    
    rank_data = rank_payload["data"]               #all rank data
    account_data = account_payload["data"]         #all account data (level etc.)


    player_data = rank_data["account"]                        #self explanatory
    player_level = account_data["account_level"]
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
    await interaction.followup.send(embed=embed)


bot.run(token=token)




