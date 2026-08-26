import discord
from discord.ext import commands
from discord import app_commands

class Utilidad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Muestra la latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! Latencia: {round(interaction.client.latency * 1000)}ms")

async def setup(bot):
    await bot.add_cog(Utilidad(bot))
