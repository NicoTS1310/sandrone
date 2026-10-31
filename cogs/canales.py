import re
import time

import discord
from discord.ext import commands
from discord import app_commands
from utils.database import init_db, get_config, set_config, add_temp_channel, remove_temp_channel, get_temp_channels


class Canales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels: set[int] = set()  # Cache en memoria de canales temporales activos
        self.mention_bursts: dict[tuple[int, int], list[tuple[float, discord.Message]]] = {}
        self.last_spam_alert: dict[tuple[int, int], float] = {}
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
            await new_channel.send(
                f"Bienvenido/a {member.mention} a tu canal de voz temporal. "
                "Se eliminará automaticamente cuando todos salgan del canal. "
                "Aquí puedes usar los comandos de música, que están deshabilitados en #general."
            )

        # ── Alguien sale de un canal → si es temporal y quedó vacío, eliminarlo
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                self.temp_channels.discard(before.channel.id)
                remove_temp_channel(before.channel.id)
                await before.channel.delete(reason="Canal temporal vacío")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        if (
            message.mention_everyone
            and not message.author.guild_permissions.administrator
            and not message.author.guild_permissions.manage_messages
        ):
            key = (message.guild.id, message.author.id)
            now = time.monotonic()
            recent_messages = [
                (timestamp, recent_message)
                for timestamp, recent_message in self.mention_bursts.get(key, [])
                if now - timestamp <= 10
            ]
            recent_messages.append((now, message))
            self.mention_bursts[key] = recent_messages

            image_extensions = (".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp")
            has_image = any(
                (attachment.content_type and attachment.content_type.startswith("image/"))
                or attachment.filename.lower().endswith(image_extensions)
                for attachment in message.attachments
            ) or any(embed.image.url or embed.thumbnail.url for embed in message.embeds)
            has_link = bool(re.search(r"(?:https?://|www\.)\S+", message.content, re.IGNORECASE)) or any(
                embed.url for embed in message.embeds
            )
            repeated_across_channels = (
                len(recent_messages) >= 3
                and len({recent_message.channel.id for _, recent_message in recent_messages}) >= 3
            )

            if (has_image or has_link) or repeated_across_channels:
                messages_to_delete = (
                    [recent_message for _, recent_message in recent_messages]
                    if repeated_across_channels
                    else [message]
                )
                for suspicious_message in messages_to_delete:
                    await suspicious_message.delete(reason="Posible spam con menciones masivas")

                last_alert = self.last_spam_alert.get(key, 0)
                if now - last_alert >= 60:
                    self.last_spam_alert[key] = now
                    alert_channel_raw = get_config(message.guild.id, "spam_alert_channel")
                    alert_channel = (
                        message.guild.get_channel(int(alert_channel_raw))
                        if alert_channel_raw
                        else None
                    )
                    alert_channel = alert_channel or message.channel
                    await alert_channel.send(
                        f"🚨 Posible spam de {message.author.mention} detectado y eliminado en "
                        f"{message.channel.mention}. Revisen la cuenta.",
                        allowed_mentions=discord.AllowedMentions.none()
                    )

        channel_raw = get_config(message.guild.id, "music_block_channel")
        if channel_raw and message.channel.id == int(channel_raw):
            content = message.content.lstrip().casefold()
            if content.startswith("m!") and len(content) > 2 and not content[2].isspace():
                await message.delete()
                await message.channel.send(
                    "Los comandos de música están deshabilitados en este canal. "
                    "Puedes usarlos en el chat del canal de voz temporal.",
                    delete_after=10,
                    allowed_mentions=discord.AllowedMentions.none()
                )

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

    @app_commands.command(
        name="canal-musica-bloqueo",
        description="Configura el canal donde se bloquean los comandos m!"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_musica_bloqueo(self, interaction: discord.Interaction, canal: discord.TextChannel):
        set_config(interaction.guild_id, "music_block_channel", str(canal.id))
        await interaction.response.send_message(
            f"✅ Los comandos que comiencen con `m!` se bloquearán en {canal.mention}.",
            ephemeral=True
        )

    @app_commands.command(
        name="canal-alertas-spam",
        description="Configura dónde se notificará el spam con menciones masivas"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_alertas_spam(self, interaction: discord.Interaction, canal: discord.TextChannel):
        set_config(interaction.guild_id, "spam_alert_channel", str(canal.id))
        await interaction.response.send_message(
            f"✅ Las alertas de posible spam se enviarán a {canal.mention}.",
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
