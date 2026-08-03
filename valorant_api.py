import aiohttp
from urllib.parse import quote

from config import HENRIK_API_KEY, ssl_context
from stats import calculate_recent_match_stats, calculate_recent_rr_change


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
