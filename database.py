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

    connection.commit()
    connection.close()


def save_player_id(discord_user_id, name, tag, region):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute(
        """
    INSERT INTO saved_players (discord_user_id, name, tag, region)
    VALUES(?,?,?,?)

    ON CONFLICT(discord_user_id) DO UPDATE SET
      name = excluded.name,
      tag = excluded.tag,
      region = excluded.region
""",
        (discord_user_id, name, tag, region),
    )

    connection.commit()
    connection.close()


def get_saved_player_id(discord_user_id):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """SELECT name, tag, region FROM saved_players WHERE discord_user_id = ?""",
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
