import sqlite3

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
    cursor.execute("""CREATE TABLE IF NOT EXISTS tracked_matches(
                match_id TEXT NOT NULL,
                discord_user_id TEXT NOT NULL,
                week_start TEXT NOT NULL,
                won INTEGER NOT NULL,
                played_at TEXT NOT NULL,
                PRIMARY KEY(match_id, discord_user_id)
        )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS weekly_scores(
                    discord_user_id TEXT NOT NULL,
                    week_start TEXT NOT NULL,
                    wins INTEGER NOT NULL DEFAULT 0,
                    matches_played INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(discord_user_id, week_start)
            )""")

    cursor.execute("PRAGMA table_info(saved_players)")
    saved_player_columns = [column[1] for column in cursor.fetchall()]

    if "puuid" not in saved_player_columns:
        cursor.execute("ALTER TABLE saved_players ADD COLUMN puuid TEXT")

    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS unique_saved_players_puuid
                      ON saved_players(puuid)
                      WHERE puuid IS NOT NULL
    """)

    connection.commit()
    connection.close()


def get_all_saved_players():
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT discord_user_id, name, tag, region, puuid FROM saved_players"""
    )

    saved_players = cursor.fetchall()

    connection.close()

    return saved_players


def has_match_been_counted(match_id, discord_user_id):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT 1
                FROM tracked_matches 
                WHERE match_id = ? 
                AND  discord_user_id = ?""",
        (match_id, discord_user_id),
    )

    counted_match = cursor.fetchone()
    connection.close()
    return counted_match is not None


def record_counted_match(match_id, discord_user_id, week_start, won, played_at):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """INSERT OR IGNORE INTO tracked_matches(
        match_id, discord_user_id, week_start, won, played_at
        ) VALUES(?, ?, ?, ?, ?)""",
        (match_id, discord_user_id, week_start, won, played_at),
    )

    if cursor.rowcount == 1:
        cursor.execute(
            """INSERT INTO weekly_scores(
            discord_user_id, week_start, wins, matches_played)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(discord_user_id, week_start)
            DO UPDATE SET
            wins = wins + excluded.wins,
            matches_played = matches_played + 1""",
            (discord_user_id, week_start, 1 if won else 0),
        )

    connection.commit()
    connection.close()


def get_weekly_leaderboard(week_start):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT discord_user_id, wins, matches_played
        FROM weekly_scores
        WHERE week_start = ?
        ORDER BY wins DESC, matches_played ASC
        """,
        (week_start,),
    )

    leaderboard_rows = cursor.fetchall()

    connection.close()

    return leaderboard_rows


def save_player_id(discord_user_id, name, tag, region, puuid):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute(
        """
    INSERT INTO saved_players (discord_user_id, name, tag, region, puuid)
    VALUES(?,?,?,?,?)

    ON CONFLICT(discord_user_id) DO UPDATE SET
      name = excluded.name,
      tag = excluded.tag,
      region = excluded.region,
      puuid = excluded.puuid
""",
        (discord_user_id, name, tag, region, puuid),
    )

    connection.commit()
    connection.close()


def get_saved_player_id(discord_user_id):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT name, tag, region, puuid FROM saved_players WHERE discord_user_id = ?""",
        (discord_user_id,),
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


def update_saved_player_puuid(discord_user_id, puuid):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE saved_players
        SET puuid = ?
        WHERE discord_user_id = ?
        """,
        (puuid, discord_user_id),
    )

    connection.commit()
    connection.close()


def get_discord_user_by_puuid(puuid):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT discord_user_id FROM saved_players WHERE puuid = ?""",
        (puuid,),
    )

    saved_user = cursor.fetchone()

    connection.close()

    return saved_user
