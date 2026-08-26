import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from utils.database import init_db, get_partner, add_marriage, remove_marriage

class MarryView(discord.ui.View):
    """Botones de Aceptar/Rechazar para la propuesta de matrimonio."""
    def __init__(self, proposer: discord.Member, target: discord.Member):
        super().__init__(timeout=60)
        self.proposer = proposer
        self.target = target

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Solo el usuario al que se le propone puede responder
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("Este mensaje no es para ti.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aceptar 💍", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        date = datetime.now().strftime("%d/%m/%Y")
        add_marriage(self.proposer.id, self.target.id, interaction.guild_id, date)
        self.stop()
        embed = discord.Embed(
            title="💍 ¡Se casaron!",
            description=f"{self.proposer.mention} y {self.target.mention} ahora están casados 🎉",
            color=discord.Color.magenta()
        )
        embed.set_footer(text=f"Casados el {date}")
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Rechazar 💔", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        embed = discord.Embed(
            title="💔 Propuesta rechazada",
            description=f"{self.target.mention} rechazó la propuesta de {self.proposer.mention}.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()  # Crea la tabla si no existe al cargar el cog

    @app_commands.command(name="marry", description="Propone matrimonio a otro usuario")
    async def marry(self, interaction: discord.Interaction, usuario: discord.Member):
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("No puedes casarte contigo mismo.", ephemeral=True)
            return
        if usuario.bot:
            await interaction.response.send_message("No puedes casarte con un bot.", ephemeral=True)
            return
        if get_partner(interaction.user.id, interaction.guild_id):
            await interaction.response.send_message("Ya estás casado/a. Usa `/divorcio` primero.", ephemeral=True)
            return
        if get_partner(usuario.id, interaction.guild_id):
            await interaction.response.send_message(f"{usuario.mention} ya está casado/a.", ephemeral=True)
            return

        embed = discord.Embed(
            title="💍 Propuesta de matrimonio",
            description=f"{interaction.user.mention} le propone matrimonio a {usuario.mention}!\n\n{usuario.mention}, ¿aceptas?",
            color=discord.Color.gold()
        )
        embed.set_footer(text="La propuesta expira en 60 segundos.")
        await interaction.response.send_message(embed=embed, view=MarryView(interaction.user, usuario))

    @app_commands.command(name="divorcio", description="Termina tu matrimonio actual")
    async def divorcio(self, interaction: discord.Interaction):
        partner_id = get_partner(interaction.user.id, interaction.guild_id)
        if not partner_id:
            await interaction.response.send_message("No estás casado/a.", ephemeral=True)
            return

        remove_marriage(interaction.user.id, interaction.guild_id)
        partner = interaction.guild.get_member(partner_id)
        partner_mention = partner.mention if partner else f"<@{partner_id}>"

        embed = discord.Embed(
            title="💔 Divorcio",
            description=f"{interaction.user.mention} y {partner_mention} ya no están casados.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pareja", description="Muestra con quién estás casado/a")
    async def pareja(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        partner_id = get_partner(target.id, interaction.guild_id)

        if not partner_id:
            msg = "No estás casado/a." if target == interaction.user else f"{target.mention} no está casado/a."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        partner = interaction.guild.get_member(partner_id)
        partner_mention = partner.mention if partner else f"<@{partner_id}>"

        embed = discord.Embed(
            title="💑 Pareja",
            description=f"{target.mention} está casado/a con {partner_mention} 💍",
            color=discord.Color.magenta()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Social(bot))
