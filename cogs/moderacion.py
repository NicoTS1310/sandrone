import discord
from discord.ext import commands
from discord import app_commands

from utils.database import (
    add_strike,
    get_strike_count,
    get_strike_history,
    get_strike_overview,
    get_strike_total,
    get_strike_user_count,
    remove_latest_strike,
)


STRIKE_PAGE_SIZE = 15


def resolve_user_id(
    usuario: discord.Member | None,
    usuario_id: str | None,
) -> tuple[int, str] | None:
    if (usuario is None) == (usuario_id is None):
        return None

    if usuario is not None:
        return usuario.id, usuario.display_name

    if not usuario_id.isascii() or not usuario_id.isdigit():
        return None

    user_id = int(usuario_id)
    if not 0 < user_id < 2**64:
        return None
    return user_id, f"ID {user_id}"


class StrikesOverviewView(discord.ui.View):
    def __init__(self, guild_id: int, administrator_id: int, page: int = 0):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.administrator_id = administrator_id
        self.page = page
        self.total_users = get_strike_user_count(guild_id)
        self.total_strikes = get_strike_total(guild_id)
        self._update_buttons()

    def _update_buttons(self):
        page_count = max(1, (self.total_users + STRIKE_PAGE_SIZE - 1) // STRIKE_PAGE_SIZE)
        self.previous_page.disabled = self.page == 0
        self.next_page.disabled = self.page >= page_count - 1

    def create_embed(self) -> discord.Embed:
        rows = get_strike_overview(
            self.guild_id,
            STRIKE_PAGE_SIZE,
            self.page * STRIKE_PAGE_SIZE,
        )
        description = "\n".join(
            f"{index}. <@{user_id}> — **{count}** strike{'s' if count != 1 else ''}"
            for index, (user_id, count) in enumerate(
                rows,
                start=self.page * STRIKE_PAGE_SIZE + 1,
            )
        )
        embed = discord.Embed(
            title="🛡️ Usuarios con strikes",
            description=description or "No hay usuarios con strikes activos.",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Usuarios", value=str(self.total_users))
        embed.add_field(name="Strikes activos", value=str(self.total_strikes))
        page_count = max(1, (self.total_users + STRIKE_PAGE_SIZE - 1) // STRIKE_PAGE_SIZE)
        embed.set_footer(text=f"Página {self.page + 1} de {page_count}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            interaction.user.id != self.administrator_id
            or not isinstance(interaction.user, discord.Member)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Solo quien abrió la vista y sigue siendo administrador puede navegarla.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
    async def previous_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Siguiente", style=discord.ButtonStyle.secondary)
    async def next_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class ConfirmarBorradoView(discord.ui.View):
    def __init__(
        self,
        canal: discord.TextChannel,
        usuario_id: int,
        usuario_nombre: str,
        administrador_id: int,
    ):
        super().__init__(timeout=120)
        self.canal = canal
        self.usuario_id = usuario_id
        self.usuario_nombre = usuario_nombre
        self.administrador_id = administrador_id
        self.mensaje: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            interaction.user.id != self.administrador_id
            or not isinstance(interaction.user, discord.Member)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Solo quien inició esta operación y sigue siendo administrador puede confirmarla.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Sí, borrar mensajes", style=discord.ButtonStyle.danger)
    async def confirmar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.mensaje = interaction.message
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"Eliminando mensajes de {self.usuario_nombre} en {self.canal.mention}…",
            view=self,
        )

        try:
            eliminados = await self.canal.purge(
                limit=None,
                check=lambda mensaje: mensaje.author.id == self.usuario_id,
                reason=(
                    f"Borrado solicitado por {interaction.user} "
                    f"({interaction.user.id})"
                ),
            )
        except discord.Forbidden:
            await self.mensaje.edit(
                content=(
                    "No pude borrar los mensajes. Comprueba que Sandrone tenga "
                    "**Ver canal**, **Leer el historial de mensajes** y "
                    "**Gestionar mensajes** en ese canal."
                ),
                view=None,
            )
        except discord.HTTPException:
            await self.mensaje.edit(
                content=(
                    "Discord devolvió un error durante el borrado. Algunos mensajes "
                    "podrían haberse eliminado antes del error; revisa el canal."
                ),
                view=None,
            )
        else:
            await self.mensaje.edit(
                content=(
                    f"✅ Eliminé {len(eliminados)} mensajes de {self.usuario_nombre} "
                    f"en {self.canal.mention}."
                ),
                view=None,
            )
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.edit_message(
            content="Borrado cancelado.",
            view=None,
        )
        self.stop()

    async def on_timeout(self):
        if self.mensaje is not None:
            await self.mensaje.edit(
                content="La confirmación expiró. No se borró ningún mensaje.",
                view=None,
            )


class Moderacion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Envía un mensaje como Sandrone")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def say(
        self,
        interaction: discord.Interaction,
        mensaje: str,
        canal: discord.TextChannel | None = None,
    ):
        if not mensaje.strip():
            await interaction.response.send_message(
                "El mensaje no puede estar vacío.",
                ephemeral=True,
            )
            return
        if len(mensaje) > 2000:
            await interaction.response.send_message(
                "El mensaje supera el límite de 2000 caracteres de Discord.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        target_channel = canal or interaction.channel
        if (
            guild is None
            or not isinstance(target_channel, discord.TextChannel)
            or target_channel.guild.id != guild.id
        ):
            await interaction.response.send_message(
                "Elige un canal de texto de este servidor.",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        permissions = (
            target_channel.permissions_for(bot_member)
            if bot_member
            else discord.Permissions.none()
        )
        if not permissions.send_messages:
            await interaction.response.send_message(
                "Sandrone no tiene permiso para enviar mensajes en ese canal.",
                ephemeral=True,
            )
            return

        try:
            await target_channel.send(
                mensaje,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord no permitió enviar el mensaje. Revisa los permisos del canal.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord no pudo enviar el mensaje. Comprueba el texto y vuelve a intentarlo.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Mensaje enviado en {target_channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="strike-agregar", description="Agrega un strike a un usuario")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def strike_agregar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None,
        usuario_id: str | None = None,
        razon: str = "Sin razón especificada",
    ):
        target = resolve_user_id(usuario, usuario_id)
        if target is None:
            await interaction.response.send_message(
                "Selecciona un usuario o escribe un ID válido, pero no ambos.",
                ephemeral=True,
            )
            return

        if not razon.strip() or len(razon) > 500:
            await interaction.response.send_message(
                "La razón debe tener entre 1 y 500 caracteres.",
                ephemeral=True,
            )
            return

        user_id, user_name = target
        add_strike(
            interaction.guild_id,
            user_id,
            interaction.user.id,
            razon.strip(),
            "manual",
        )
        count = get_strike_count(interaction.guild_id, user_id)
        await interaction.response.send_message(
            f"✅ Strike agregado a **{user_name}**. Tiene **{count}** strike"
            f"{'s' if count != 1 else ''} activo(s).",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="strike-quitar",
        description="Retira el strike activo más reciente de un usuario"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def strike_quitar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None,
        usuario_id: str | None = None,
    ):
        target = resolve_user_id(usuario, usuario_id)
        if target is None:
            await interaction.response.send_message(
                "Selecciona un usuario o escribe un ID válido, pero no ambos.",
                ephemeral=True,
            )
            return

        user_id, user_name = target
        removed = remove_latest_strike(
            interaction.guild_id,
            user_id,
            interaction.user.id,
        )
        if not removed:
            await interaction.response.send_message(
                f"**{user_name}** no tiene strikes activos.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        count = get_strike_count(interaction.guild_id, user_id)
        await interaction.response.send_message(
            f"✅ Retiré el strike activo más reciente de **{user_name}**. "
            f"Le quedan **{count}** strike{'s' if count != 1 else ''}.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="strikes-usuario",
        description="Muestra los strikes activos de un usuario"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def strikes_usuario(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None,
        usuario_id: str | None = None,
    ):
        target = resolve_user_id(usuario, usuario_id)
        if target is None:
            await interaction.response.send_message(
                "Selecciona un usuario o escribe un ID válido, pero no ambos.",
                ephemeral=True,
            )
            return

        user_id, user_name = target
        count = get_strike_count(interaction.guild_id, user_id)
        history = get_strike_history(interaction.guild_id, user_id)
        embed = discord.Embed(
            title=f"Strikes de {user_name}",
            description=f"**Strikes activos:** {count}",
            color=discord.Color.orange() if count else discord.Color.green(),
        )
        if history:
            embed.add_field(
                name="Incidencias recientes",
                value="\n".join(
                    f"• `{created_at}` — **{source}**: {reason[:300]}"
                    for reason, created_at, source in history
                ),
                inline=False,
            )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="strikes-lista",
        description="Muestra los usuarios con strikes activos en el servidor"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def strikes_lista(self, interaction: discord.Interaction):
        view = StrikesOverviewView(
            interaction.guild_id,
            interaction.user.id,
        )
        await interaction.response.send_message(
            embed=view.create_embed(),
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="borrar-mensajes",
        description="Borra los mensajes de un usuario en un canal (requiere confirmación)"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def borrar_mensajes(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        usuario: discord.Member | None = None,
        usuario_id: str | None = None,
    ):
        target = resolve_user_id(usuario, usuario_id)
        if target is None:
            await interaction.response.send_message(
                "Selecciona un usuario o escribe un ID válido, pero no ambos.",
                ephemeral=True,
            )
            return

        target_id, target_name = target

        guild = interaction.guild
        if guild is None or guild.id != canal.guild.id:
            await interaction.response.send_message(
                "El canal debe pertenecer a este servidor.",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        permissions = canal.permissions_for(bot_member) if bot_member else discord.Permissions.none()
        if not permissions.read_message_history or not permissions.manage_messages:
            await interaction.response.send_message(
                "Sandrone necesita los permisos **Leer el historial de mensajes** "
                "y **Gestionar mensajes** en ese canal.",
                ephemeral=True,
            )
            return

        view = ConfirmarBorradoView(
            canal,
            target_id,
            target_name,
            interaction.user.id,
        )
        await interaction.response.send_message(
            f"⚠️ ¿Seguro que quieres borrar **todos los mensajes** de "
            f"**{target_name}** en {canal.mention}? Esta acción no se puede deshacer.",
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.mensaje = await interaction.original_response()

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
