import discord

class CustomLobby:
  def __init__(self, host, required_members):
    self.host = host
    self.required_members = required_members
    self.players = []

  def add_player(self, player):
    if player in self.players:
      return False

    if len(self.players) >= self.required_members:
      return False

    self.players.append(player)
    return True

  def remove_player(self, player):
    if player not in self.players:
      return False

    self.players.remove(player)
    return True


  def is_full(self):
    return len(self.players) >= self.required_members


  def get_player_list_text(self):
    if not self.players:
      return "No players joined yet."

    player_mentions = []

    for player in self.players:
      player_mentions.append(player.mention)

    return "\n".join(player_mentions)


def build_lobby_embed(lobby):
  embed = discord.Embed(
  title="Valorant Custom Lobby",
  description=f"Host: {lobby.host.mention}",
  color = discord.Color.red()
  )

  embed.add_field(
    name=f"Players ({len(lobby.players)}/{lobby.required_members})",
    value=lobby.get_player_list_text(),
    inline=False
  )

  return embed

class CustomLobbyView(discord.ui.View):
  def __init__(self, lobby):
    super().__init__(timeout=1800)
    self.lobby = lobby

  @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
  async def join_button(self, interaction, button):
    added = self.lobby.add_player(interaction.user)

    if not added:
      await interaction.response.send_message(
        "You are already in the lobby, or the lobby is full",
        ephemeral = True,
      )
      return

    embed = build_lobby_embed(self.lobby)

    await interaction.response.edit_message(embed=embed, view=self)


  @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
  async def leave_button(self, interaction, button):
    removed = self.lobby.remove_player(interaction.user)

    if not removed:
      await interaction.response.send_message(
        "You are not in this lobby.",
        ephemeral=True,
      )
      return

    embed = build_lobby_embed(self.lobby)

    await interaction.response.edit_message(embed=embed, view=self)