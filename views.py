import aiohttp
import asyncio
from urllib.parse import quote

import discord

from config import HENRIK_API_KEY, ssl_context
from constants import MODE_LABELS
from stats import build_match_table, calculate_recent_stats
from valorant_api import build_match_url


class ModeSelect(discord.ui.Select):
    def __init__(
        self, player_name, player_tag, region_value, region_name, player_puuid, embed
    ):

        self.player_name = player_name
        self.player_tag = player_tag
        self.region_value = region_value
        self.region_name = region_name
        self.player_puuid = player_puuid
        self.embed = embed
        options = [
            discord.SelectOption(label="All", value="all"),
            discord.SelectOption(label="Competitive", value="competitive"),
            discord.SelectOption(label="Unrated", value="unrated"),
            discord.SelectOption(label="Spike Rush", value="spikerush"),
            discord.SelectOption(label="Team Deathmatch", value="teamdeathmatch"),
            discord.SelectOption(label="Deathmatch", value="deathmatch"),
            discord.SelectOption(label="Swiftplay", value="swiftplay"),
        ]

        super().__init__(
            placeholder="Choose match mode",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_mode = self.values[0]

        safe_name = quote(self.player_name, safe="")
        safe_tag = quote(self.player_tag, safe="")

        matches_url = build_match_url(
            self.region_value, safe_name, safe_tag, selected_mode
        )

        headers = {"Authorization": HENRIK_API_KEY}
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession(
                headers=headers, timeout=timeout, connector=connector
            ) as session:
                async with session.get(matches_url) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            f"Could not load {selected_mode} matches. Error {response.status}.",
                            ephemeral=True,
                        )
                        return
                    matches_payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await interaction.followup.send(
                "Could not reach the Valorant API. Please try again shortly.",
                ephemeral=True,
            )
            return
        mode_label = MODE_LABELS[selected_mode]

        self.embed.set_field_at(
            index=3,
            name=f"{mode_label} Summary",
            value=calculate_recent_stats(matches_payload, self.player_puuid),
            inline=False,
        )

        self.embed.set_field_at(
            index=4,
            name=f"Recent {mode_label} Matches",
            value=build_match_table(matches_payload, self.player_puuid),
            inline=False,
        )

        await interaction.message.edit(embed=self.embed, view=self.view)


class ModeView(discord.ui.View):
    def __init__(
        self, player_name, player_tag, region_value, region_name, player_puuid, embed
    ):
        super().__init__(timeout=120)
        self.add_item(
            ModeSelect(
                player_name, player_tag, region_value, region_name, player_puuid, embed
            )
        )
