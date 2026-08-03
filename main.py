import aiohttp
import asyncio
from urllib.parse import quote
import discord
from database import setup_db, save_player_id, get_saved_player_id, delete_player_id
from constants import MODE_LABELS, REGION_LABELS, RANK_VALUES
from stats import (
    build_match_table,
    build_compare_verdict,
    calculate_recent_stats,
    calculate_recent_match_stats,
    calculate_recent_rr_change,
)
from config import DISCORD_TOKEN, HENRIK_API_KEY, ssl_context
from valorant_api import build_match_url, fetch_compare_data
from views import ModeView
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(activity=discord.Game("/help"))
    synced_commands = await bot.tree.sync()
    print(f"Synced {len(synced_commands)} slash command(s).")


async def send_valstats(interaction, name, tag, region_value, region_name):
    await interaction.response.defer(thinking=True)

    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region_value}/pc/{safe_name}/{safe_tag}"
    account_url = (
        f"https://api.henrikdev.xyz/valorant/v1/account/{safe_name}/{safe_tag}"
    )
    matches_url = build_match_url(region_value, safe_name, safe_tag)
    mmr_history_url = f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region_value}/pc/{safe_name}/{safe_tag}"

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    try:
        async with aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=connector,
        ) as session:
            async with session.get(rank_url) as response:
                if response.status == 404:
                    await interaction.followup.send(
                        "Could not find this player. Check the name, tag and region."
                    )
                    return
                if response.status != 200:
                    await interaction.followup.send(
                        f"Valorant API returned error {response.status}. Try again shortly."
                    )
                    return
                rank_payload = await response.json()
            async with session.get(account_url) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"Found the player, but could not load their account level. Error {response.status}."
                    )
                    return
                account_payload = await response.json()
            async with session.get(matches_url) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"Found the player, but could not load their match history. Error {response.status}."
                    )
                    return
                matches_payload = await response.json()
            async with session.get(mmr_history_url) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        f"Found the player, but could not load their RR history. Error {response.status}."
                    )
                    return
                mmr_history_payload = await response.json()

    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        print(f"HenrikDev request failed: {type(error).__name__}: {error!r}")
        await interaction.followup.send(
            "Could not reach the Valorant API. Please try again shortly"
        )
        return

    rank_data = rank_payload["data"]  # all rank data
    account_data = account_payload["data"]  # all account data (level etc.)

    player_data = rank_data["account"]  # self explanatory
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
        description=f"**Peak: {player_peak_rank}**",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="Level",
        value=f"{player_level}",
        inline=True,
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
        name="Recent Summary",
        value=calculate_recent_stats(matches_payload, player_puuid),
        inline=False,
    )
    embed.set_footer(text=f"{region_name} • PC")

    embed.add_field(
        name="All Recent Matches",
        value=build_match_table(
            matches_payload=matches_payload, player_puuid=player_puuid
        ),
        inline=False,
    )
    await interaction.followup.send(
        embed=embed,
        view=ModeView(
            player_name, player_tag, region_value, region_name, player_puuid, embed
        ),
    )


@bot.tree.command(
    name="valstats",
    description="Show a Valorant player's recent stats.",
)
@app_commands.choices(
    region=[
        app_commands.Choice(name="Asia Pacific", value="ap"),
        app_commands.Choice(name="North America", value="na"),
        app_commands.Choice(name="Europe", value="eu"),
        app_commands.Choice(name="Korea", value="kr"),
        app_commands.Choice(name="Latin America", value="latam"),
        app_commands.Choice(name="Brazil", value="br"),
    ]
)
async def valstat(
    interaction: discord.Interaction,
    name: str,
    tag: str,
    region: app_commands.Choice[str],
):
    await send_valstats(interaction, name, tag, region.value, region.name)


@bot.tree.command(
    name="setid", description="Save your valorant ID for quick stat lookups."
)
@app_commands.choices(
    region=[
        app_commands.Choice(name="Asia Pacific", value="ap"),
        app_commands.Choice(name="North America", value="na"),
        app_commands.Choice(name="Europe", value="eu"),
        app_commands.Choice(name="Korea", value="kr"),
        app_commands.Choice(name="Latin America", value="latam"),
        app_commands.Choice(name="Brazil", value="br"),
    ]
)
async def setid(
    interaction: discord.Interaction,
    name: str,
    tag: str,
    region: app_commands.Choice[str],
):
    discord_user_id = str(interaction.user.id)

    save_player_id(discord_user_id, name, tag, region.value)

    await interaction.response.send_message(
        f"Set your Valorant ID **{name}#{tag}** in **{region.name}**.", ephemeral=True
    )


@bot.tree.command(name="myid", description="View your saved Valorant ID")
async def myid(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)

    saved_player = get_saved_player_id(discord_user_id)

    if saved_player == None:
        await interaction.response.send_message(
            "You do not have a saved Valorant ID yet. Use '/setid' first.",
            ephemeral=True,
        )
        return

    name, tag, region = saved_player

    region_label = REGION_LABELS[region]

    await interaction.response.send_message(
        f"Your saved Valorant ID is **{name}#{tag}** in region **{region_label}**",
        ephemeral=True,
    )


@bot.tree.command(name="unsetid", description="Remove your saved Valorant ID")
async def unsetid(interaction: discord.Interaction):
    saved_player_id = str(interaction.user.id)

    deleted_count = delete_player_id(saved_player_id)

    if deleted_count == 0:
        await interaction.response.send_message(
            "You do not have a saved Valorant ID to remove.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "Removed you saved valorant ID.", ephemeral=True
    )


@bot.tree.command(
    name="valstatsme", description="Show stats for your saved Valorant ID."
)
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
    name="valstatsuser",
    description="Show stats for Discord user's if they have linked Valorant ID.",
)
async def valstatuser(interaction: discord.Interaction, user: discord.User):
    discord_user_id = str(user.id)

    saved_player = get_saved_player_id(discord_user_id)

    if saved_player is None:
        await interaction.response.send_message(
            f"{user.mention} does not have a linked Valorant ID yet.", ephemeral=True
        )
        return

    name, tag, region = saved_player
    region_name = REGION_LABELS[region]

    await send_valstats(interaction, name, tag, region, region_name)


@bot.tree.command(name="help", description="Show all Valobot commands.")
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


@bot.tree.command(name="compare", description="Compare two linked Valorant players.")
async def compare(
    interaction: discord.Interaction, user1: discord.User, user2: discord.User
):
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
        name="Rank", value=f"{player1['rank']} vs {player2['rank']}", inline=False
    )

    embed.add_field(
        name="Recent RR Change",
        value=f"{player1['rr_change']:+} vs {player2['rr_change']:+}",
        inline=False,
    )

    embed.add_field(
        name="Recent Record",
        value=f"{player1['wins']}W-{player1['losses']}L vs {player2['wins']}W-{player2['losses']}L",
        inline=False,
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
bot.run(token=DISCORD_TOKEN)
