import discord
from discord.ext import commands
from discord import app_commands

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) #tiempo que dura el menu activo

        #Menu desplegable
        options = [
            discord.SelectOption(label="miscelaneo", description="Comandos varios", emoji="👾", value="miscelaneo"),
            discord.SelectOption(label="moderacion", description="Comandos para mods", emoji="🛡️", value="moderacion"),
            discord.SelectOption(label="utilidad", description="Comandos utiles", emoji="🔧", value="utilidad"),
            discord.SelectOption(label="social", description="Comandos sociales", emoji="💍", value="social"),
        ]
        self.select = discord.ui.Select(placeholder="Elige una categoría...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        categoria = self.select.values[0]

        embed = discord.Embed(
            title="Ayuda de sandrone",
            color=discord.Color.teal()
        )

        #Embed q cambia con menu desplegable
        embed.set_thumbnail(url="")

        if categoria == "miscelaneo":
            embed.description = "Comandos miscelaneos / aleatorios"
            embed.add_field(name="Comandos", value="/suma - Suma 2 numeros\n/compatibilidad - Calcula la compatibilidad entre 2 usuarios")

        elif categoria == "moderacion":
            embed.description = "Comandos de moderacion"
            embed.add_field(name="Comandos", value="/ban - Banea un usuario\n/kick - Expulsa un usuario")

        elif categoria == "social":
            embed.description = "Comandos sociales"
            embed.add_field(name="Comandos", value="/marry - Propone matrimonio\n/divorcio - Termina tu matrimonio\n/pareja - Muestra tu pareja actual")

        #agregar mas con "elif"
        embed.set_footer(text="Sandrone bot - Selecciona otra categoria en el menu")
        await interaction.response.edit_message(embed=embed, view=self)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Muestra la lista de comandos de sandrone")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Ayuda de sandrone",
            description="Selecciona una categoria en el menu desplegable abajo para ver los comandos",
            color=discord.Color.teal()
        )
        embed.set_thumbnail(url="")
        embed.set_footer(text="Sandrone Bot")

        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))