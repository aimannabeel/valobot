import asyncio
from database import get_all_saved_players, update_saved_player_puuid
from valorant_api import fetch_player_puuid


async def main():
    saved_players = get_all_saved_players()

    for discord_user_id, name, tag, region, puuid in saved_players:
        if puuid:
            print(f"Skipping {name}#{tag}, already has puuid.")
            continue

        print(f"Fetching puuid for {name}#{tag}...")

        fetched_puuid = await fetch_player_puuid(name, tag, region)

        if fetched_puuid is None:
            print(f"Could not fetch puuid for {name}#{tag}.")
            continue

        update_saved_player_puuid(discord_user_id, fetched_puuid)

        print(f"Updated {name}#{tag}.")


asyncio.run(main())