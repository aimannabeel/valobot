import aiohttp
import asyncio
from urllib.parse import quote
import discord
from database import (
    setup_db,
    save_player_id,
    get_saved_player_id,
    delete_player_id,
    get_weekly_leaderboard,
    get_discord_user_by_puuid,
)
from constants import MODE_LABELS, REGION_LABELS, RANK_VALUES
from datetime import datetime, timedelta, timezone
from leaderboard import refresh_weekly_leaderboard, refresh_all_leaderboards
from stats import (
    build_match_table,
    build_compare_verdict,
    calculate_recent_stats,
    calculate_recent_match_stats,
    calculate_recent_rr_change,
)
from config import DISCORD_TOKEN, HENRIK_API_KEY, ssl_context
from valorant_api import (
    build_match_url,
    fetch_compare_data,
    send_valstats_data,
    fetch_player_puuid,
)
from views import ModeView
from discord import app_commands
from discord.ext import commands, tasks
from time_utils import get_current_week_start

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)
refresh_starter_started = False


@tasks.loop(hours=1)
async def refresh_leaderboards_task():
    print("Refreshing leaderboard cache...")
    await refresh_all_leaderboards()
    print("Finished refreshing leaderboard cache.")


async def start_refresh_task_on_next_hour():
    now = datetime.now(timezone.utc)

    next_hour = (now + timedelta(hours=1)).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    seconds_until_next_hour = (next_hour - now).total_seconds()
    print(
        f"Leaderboard refresh task will start in {seconds_until_next_hour:.0f} seconds."
    )

    await asyncio.sleep(seconds_until_next_hour)

    if not refresh_leaderboards_task.is_running():
        refresh_leaderboards_task.start()
        print("Leaderboard refresh task started.")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(activity=discord.Game("/help"))
    synced_commands = await bot.tree.sync()
    print(f"Synced {len(synced_commands)} slash command(s).")

    # leaderboard refresh is paused for now
    # global refresh_starter_started

    # if not refresh_starter_started:
    #     refresh_starter_started = True
    #     asyncio.create_task(start_refresh_task_on_next_hour())


async def send_valstats(interaction, name, tag, region_value, region_name):
    await interaction.response.defer(thinking=True)

    try:
        valstats_data = await send_valstats_data(name, tag, region_value)
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        print(f"HenrikDev request failed: {type(error).__name__}: {error!r}")
        await interaction.followup.send(
            "Could not reach the Valorant API. Please try again shortly"
        )
        return

    if not valstats_data["ok"]:
        await interaction.followup.send(valstats_data["message"])
        return

    player_name = valstats_data["player_name"]
    player_tag = valstats_data["player_tag"]
    player_level = valstats_data["player_level"]
    player_puuid = valstats_data["player_puuid"]
    player_rank = valstats_data["player_rank"]
    player_peak_rank = valstats_data["player_peak_rank"]
    player_rr = valstats_data["player_rr"]
    recent_rr_change = valstats_data["recent_rr_change"]
    matches_payload = valstats_data["matches_payload"]

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
    puuid = await fetch_player_puuid(name, tag, region.value)

    if puuid is None:
        await interaction.response.send_message(
            "Could not find this player. Check the name, tag, and region.",
            ephemeral=True,
        )
        return

    linked_user = get_discord_user_by_puuid(puuid)

    if linked_user is not None and linked_user[0] != discord_user_id:
        await interaction.response.send_message(
            "This Valorant account is already linked to another Discord user.",
            ephemeral=True,
        )
        return

    save_player_id(discord_user_id, name, tag, region.value, puuid)

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

    name, tag, region, puuid = saved_player

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

    name, tag, region, puuid = saved_player
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

    name, tag, region, puuid = saved_player
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

    name1, tag1, region1, puuid1 = saved_player1
    name2, tag2, region2, puuid2 = saved_player2

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


@bot.tree.command(
    name="leaderboard", description="Show this week's server Valorant leaderboard."
)
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    await interaction.followup.send(
        "Leaderboard is paused for now while I rework it. Use `/valstatsme` or `/compare` meanwhile."
    )
    return

    week_start = get_current_week_start()

    leaderboard_rows = get_weekly_leaderboard(week_start)

    if not leaderboard_rows:
        await interaction.followup.send(
            "No leaderboard data yet. Players need to link their Valorant ID with `/setid` first."
        )
        return

    leaderboard_lines = []
    position = 1

    for row in leaderboard_rows:
        discord_user_id, wins, _ = row
        member = interaction.guild.get_member(int(discord_user_id))

        if member is None:
            try:
                member = await interaction.guild.fetch_member(int(discord_user_id))
            except discord.NotFound:
                continue

        if position == 1:
            leaderboard_lines.append(f"🏆 <@{discord_user_id}> — **{wins} wins**")
        elif position == 2:
            leaderboard_lines.append(f"🥈 <@{discord_user_id}> — **{wins} wins**")
        elif position == 3:
            leaderboard_lines.append(f"🥉 <@{discord_user_id}> — **{wins} wins**")
        else:
            leaderboard_lines.append(
                f"**#{position}** <@{discord_user_id}> — **{wins} wins**"
            )
        position += 1

    if not leaderboard_lines:
        await interaction.followup.send(
            "No leaderboard data yet for this server. Players need to link their Valorant ID with `/setid` first."
        )
        return

    embed = discord.Embed(
        title="Weekly Valorant Leaderboard",
        description="\n".join(leaderboard_lines),
        color=discord.Color.gold(),
    )

    embed.set_footer(text=f"Week starting {week_start}. To participate use '/setid'")
    await interaction.followup.send(embed=embed)


setup_db()
bot.run(token=DISCORD_TOKEN)
