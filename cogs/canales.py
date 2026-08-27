import discord
from discord.ext import commands
from discord import app_commands
from utils.database import init_db, get_config, set_config, add_temp_channel, remove_temp_channel, get_temp_channels

class Canales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels: set[int] = set()  # Cache en memoria de canales temporales activos
        init_db()

    async def cog_load(self):
        """Al cargar el cog, recupera los canales temporales guardados en la BD
        y elimina los que quedaron vacios si el bot se reinicio."""
        for guild in self.bot.guilds:
            for channel_id in get_temp_channels(guild.id):
                channel = guild.get_channel(channel_id)
                if channel is None:
                    # El canal ya no existe, limpiar de la BD
                    remove_temp_channel(channel_id)
                elif len(channel.members) == 0:
                    # Quedó vacío por el reinicio, eliminarlo
                    await channel.delete(reason="Canal temporal vacío (limpieza al reiniciar)")
                    remove_temp_channel(channel_id)
                else:
                    # Aún tiene gente, seguir rastreándolo
                    self.temp_channels.add(channel_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        hub_raw = get_config(member.guild.id, "hub_channel")
        if not hub_raw:
            return
        hub_id = int(hub_raw)

        # ── Alguien entra al canal hub → crear canal temporal y mover al usuario
        if after.channel and after.channel.id == hub_id:
            category = after.channel.category
            new_channel = await member.guild.create_voice_channel(
                name=f"🎮 {member.display_name}",
                category=category,
                reason="Canal temporal automático"
            )
            self.temp_channels.add(new_channel.id)
            add_temp_channel(new_channel.id, member.guild.id)
            await member.move_to(new_channel)

        # ── Alguien sale de un canal → si es temporal y quedó vacío, eliminarlo
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                self.temp_channels.discard(before.channel.id)
                remove_temp_channel(before.channel.id)
                await before.channel.delete(reason="Canal temporal vacío")

    # ── Comando para configurar el canal hub ─────────────────────────────────
    @app_commands.command(name="canal-hub", description="Configura el canal de voz que crea salas temporales")
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_hub(self, interaction: discord.Interaction, canal: discord.VoiceChannel):
        set_config(interaction.guild_id, "hub_channel", str(canal.id))
        await interaction.response.send_message(
            f"✅ Canal hub configurado: **{canal.name}**\n"
            f"Cada vez que alguien se una ahí se creará una sala temporal automáticamente.",
            ephemeral=True
        )

    @app_commands.command(name="canal-hub-ver", description="Muestra cuál es el canal hub configurado")
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_hub_ver(self, interaction: discord.Interaction):
        hub_raw = get_config(interaction.guild_id, "hub_channel")
        if not hub_raw:
            await interaction.response.send_message("No hay ningún canal hub configurado. Usa `/canal-hub`.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(hub_raw))
        name = channel.mention if channel else f"Canal eliminado (ID: {hub_raw})"
        await interaction.response.send_message(f"Canal hub actual: {name}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Canales(bot))
