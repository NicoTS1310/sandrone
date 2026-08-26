import discord
from discord.ext import commands
from discord import app_commands

class Moderacion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Banea a un usuario")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razon especificada"):
        await usuario.ban(reason=razon)
        await interaction.response.send_message(f"{usuario.mention} ha sido baneado. Razon: {razon}")

    @app_commands.command(name="kick", description="Expulsa a un usuario")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razon especificada"):
        await usuario.kick(reason=razon)
        await interaction.response.send_message(f"{usuario.mention} ha sido expulsado. Razon: {razon}")

async def setup(bot):
    await bot.add_cog(Moderacion(bot))
