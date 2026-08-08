from time_utils import get_current_week_start
from database import get_all_saved_players, record_counted_match
from stats import did_player_win_match
from valorant_api import fetch_weekly_competitive_matches
import discord
import asyncio


async def refresh_weekly_leaderboard(guild):
    week_start = get_current_week_start()
    saved_players = get_all_saved_players()

    for discord_user_id, name, tag, region, puuid in saved_players:
        member = guild.get_member(int(discord_user_id))

        if member is None:
            try:
                member = await guild.fetch_member(int(discord_user_id))
            except discord.NotFound:
                continue
        weekly_matches = await fetch_weekly_competitive_matches(
            name, tag, region, week_start
        )

        if weekly_matches is None:
            await asyncio.sleep(5)
            continue
        for match in weekly_matches:
            match_id = match["metadata"]["match_id"]
            played_at = match["metadata"]["started_at"]
            won = did_player_win_match(match, puuid)

            if won is None:
                continue

            record_counted_match(match_id, discord_user_id, week_start, won, played_at)
        await asyncio.sleep(5)

    return week_start


async def refresh_all_leaderboards():
    week_start = get_current_week_start()
    saved_players = get_all_saved_players()

    for discord_user_id, name, tag, region, puuid in saved_players:
        weekly_matches = await fetch_weekly_competitive_matches(
            name, tag, region, week_start
        )

        if weekly_matches is None:
            await asyncio.sleep(180)
            continue

        for match in weekly_matches:
            match_id = match["metadata"]["match_id"]
            played_at = match["metadata"]["started_at"]
            won = did_player_win_match(match, puuid)

            if won is None:
                continue

            record_counted_match(
                match_id,
                discord_user_id,
                week_start,
                won,
                played_at,
            )

        await asyncio.sleep(180)

    return week_start
