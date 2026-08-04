import aiohttp
from urllib.parse import quote

from config import HENRIK_API_KEY, ssl_context
from stats import calculate_recent_match_stats, calculate_recent_rr_change
from leaderboard import is_match_in_week


def build_match_url(region_value, safe_name, safe_tag, mode="all", size=5, start=0):
    base_url = f"https://api.henrikdev.xyz/valorant/v4/matches/{region_value}/pc/{safe_name}/{safe_tag}"

    if mode == "all":
        return f"{base_url}?size={size}&start={start}"

    return f"{base_url}?size={size}&start={start}&mode={mode}"


async def fetch_player_puuid(name, tag, region_value):
    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region_value}/pc/{safe_name}/{safe_tag}"

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(
        headers=headers,
        timeout=timeout,
        connector=connector,
    ) as session:
        async with session.get(rank_url) as response:
            if response.status != 200:
                return None

            rank_payload = await response.json()

    return rank_payload["data"]["account"]["puuid"]


async def fetch_compare_data(name, tag, region_value):
    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    rank_url = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region_value}/pc/{safe_name}/{safe_tag}"
    matches_url = build_match_url(region_value, safe_name, safe_tag, "competitive")
    mmr_history_url = f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region_value}/pc/{safe_name}/{safe_tag}"

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(
        headers=headers,
        timeout=timeout,
        connector=connector,
    ) as session:
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


async def send_valstats_data(name, tag, region_value):
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

    async with aiohttp.ClientSession(
        headers=headers,
        timeout=timeout,
        connector=connector,
    ) as session:
        async with session.get(rank_url) as response:
            if response.status == 404:
                return {
                    "ok": False,
                    "message": "Could not find this player. Check the name, tag and region.",
                }
            if response.status != 200:
                return {
                    "ok": False,
                    "message": f"Valorant API returned error {response.status}. Try again shortly.",
                }
            rank_payload = await response.json()
        async with session.get(account_url) as response:
            if response.status != 200:
                return {
                    "ok": False,
                    "message": f"Found the player, but could not load their account level. Error {response.status}.",
                }

            account_payload = await response.json()

        async with session.get(matches_url) as response:
            if response.status != 200:
                return {
                    "ok": False,
                    "message": f"Found the player, but could not load their match history. Error {response.status}.",
                }

            matches_payload = await response.json()

        async with session.get(mmr_history_url) as response:
            if response.status != 200:
                return {
                    "ok": False,
                    "message": f"Found the player, but could not load their RR history. Error {response.status}.",
                }
            mmr_history_payload = await response.json()

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

    return {
        "ok": True,
        "player_name": player_name,
        "player_tag": player_tag,
        "player_puuid": player_puuid,
        "player_level": player_level,
        "player_rank": player_rank,
        "player_peak_rank": player_peak_rank,
        "player_rr": player_rr,
        "recent_rr_change": recent_rr_change,
        "matches_payload": matches_payload,
    }


async def fetch_weekly_competitive_matches(name, tag, region_value, week_start):
    safe_name = quote(name, safe="")
    safe_tag = quote(tag, safe="")

    headers = {"Authorization": HENRIK_API_KEY}
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    weekly_matches = []
    start = 0
    size = 10
    keep_fetching = True

    async with aiohttp.ClientSession(
        headers=headers,
        timeout=timeout,
        connector=connector,
    ) as session:
        while keep_fetching:
            matches_url = build_match_url(
                region_value, safe_name, safe_tag, "competitive", size, start
            )
            async with session.get(matches_url) as response:
                if response.status != 200:
                    return None

                matches_payload = await response.json()

            matches = matches_payload["data"]

            if not matches:
                break

            for match in matches:
                if not match["metadata"]["is_completed"]:
                    continue

                started_at = match["metadata"]["started_at"]

                if is_match_in_week(started_at, week_start):
                    weekly_matches.append(match)
                else:
                    keep_fetching = False
                    break

            start += size

    return weekly_matches
