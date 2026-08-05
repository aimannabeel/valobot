from constants import RANK_VALUES

def find_matching_player(match, player_puuid):
    for player in match["players"]:
                if player["puuid"] == player_puuid:
                    return player
    return None

def find_matching_team(match, team_id):
    for team in match["teams"]:
                if team["team_id"] == team_id:
                    return team
    return None

def build_match_table(matches_payload, player_puuid):
    match_rows = []

    for match in matches_payload["data"]:
        matching_player = find_matching_player(match, player_puuid)

        if matching_player is None:
            continue

        player_team_id = matching_player["team_id"]

        matching_team = find_matching_team(match, player_team_id)

        if matching_team is None:
            continue

        mode = match["metadata"]["queue"]["name"]

        if mode == "Deathmatch":
            player_score = matching_player["stats"]["score"]

            highest_score = 0

            for player in match["players"]:
                player_score_in_match = player["stats"]["score"]

                if player_score_in_match > highest_score:
                    highest_score = player_score_in_match

            if player_score == highest_score:
                match_win_status = "🟩 Victory"
            else:
                match_win_status = "🟥 Defeat"

        elif matching_team["won"]:
            match_win_status = "🟩 Victory"
        elif match["teams"][0]["won"] == False and match["teams"][1]["won"] == False:
            match_win_status = "🟧 Draw"
        else:
            match_win_status = "🟥 Defeat"
     
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

    kd = total_kills / total_deaths if total_deaths > 0 else total_kills

    total_shots = total_headshots + total_bodyshots + total_legshots
    hs_percent = (total_headshots / total_shots) * 100 if total_shots > 0 else 0

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
            wins += 1
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
        return (
            f"Someone check {user1.mention}'s aimlabs hours. get rekt {user2.mention}"
        )

    if player2_score > player1_score:
        return f"{user2.mention} ez win get clapped {user1.mention}. "

    return "This one is too close to call. Run it back and settle it in ranked."
