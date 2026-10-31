import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.database import get_config, set_config

logger = logging.getLogger(__name__)


class Bienvenidas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_to_configured_channel(
        self,
        guild: discord.Guild,
        config_key: str,
        message: str,
        allowed_mentions: discord.AllowedMentions | None = None,
    ):
        channel_raw = get_config(guild.id, config_key)
        if not channel_raw:
            return

        channel = guild.get_channel(int(channel_raw))
        if channel is None:
            logger.warning(
                "El canal configurado con la clave %s ya no existe en el servidor %s",
                config_key,
                guild.id,
            )
            return

        await channel.send(
            message,
            allowed_mentions=allowed_mentions or discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._send_to_configured_channel(
            member.guild,
            "welcome_channel",
            f"🎉 ¡Demos la bienvenida a {member.mention}! "
            f"Ahora somos {member.guild.member_count} miembros.",
            discord.AllowedMentions(users=[member]),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._send_to_configured_channel(
            member.guild,
            "goodbye_channel",
            f"👋 {member.display_name} ha salido del servidor. "
            f"Ahora somos {member.guild.member_count} miembros.",
        )

    @app_commands.command(
        name="canal-bienvenida",
        description="Configura dónde se anuncian las nuevas personas"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_bienvenida(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        set_config(interaction.guild_id, "welcome_channel", str(canal.id))
        await interaction.response.send_message(
            f"✅ Las bienvenidas se enviarán en {canal.mention}.",
            ephemeral=True,
        )

    @app_commands.command(
        name="canal-despedida",
        description="Configura dónde se anuncian las salidas del servidor"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def canal_despedida(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        set_config(interaction.guild_id, "goodbye_channel", str(canal.id))
        await interaction.response.send_message(
            f"✅ Las despedidas se enviarán en {canal.mention}.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Bienvenidas(bot))
