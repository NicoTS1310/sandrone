import discord
import random
from discord.ext import commands
from discord import app_commands

class Miscelaneo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="suma", description="Suma dos números tampoco se pasen de rosca skdjskdj")
    async def suma(self, interaction: discord.Interaction, numero1: float, numero2: float):
        resultado = numero1 + numero2
        await interaction.response.send_message(
            f"La suma de **{numero1}** + **{numero2}** es: **{resultado}**"
        )

    @app_commands.command(name="compatibilidad", description="Calcula la compatibilidad entre 2 usuarios")
    async def compatibilidad (self, interaction: discord.Interaction, usuario1: discord.Member, usuario2: discord.Member = None):
        if usuario2 is None:
            await interaction.response.send_message("Pq tan solito 💀", ephemeral=True)
            return
        if usuario1.id == usuario2.id:
            await interaction.response.send_message("No puedes calcular la compatibilidad contigo mismo 💀", ephemeral=True)
            return

        porcentaje = random.randint(0, 100)

        #Mensajes para porcentaje — de mayor a menor para que los elif funcionen
        if porcentaje >= 99:
            mensaje= "¡Párenlo ahí! Esto es un peligro para la sociedad. Son tan iguales que si se juntan, causan un apagón en el servidor. ¡Bauticen al pelao de una vez!"
        elif porcentaje >= 95:
            mensaje= "Par de joyitas. Están hechos el uno para el otro, principalmente para que nadie más se los tenga que aguantar."
        elif porcentaje >= 90:
            mensaje= "Nivel de compatibilidad: 'Si tú robas, yo te espero en la moto'. Una sociedad del crimen perfecta."
        elif porcentaje >= 85:
            mensaje= "Demasiada bandera junta. Se complementan tanto para lo bueno como para las malas mañas. Peligrosos."
        elif porcentaje >= 78:
            mensaje= "Están a una mirada coqueta de terminar viviendo juntos en un cuarto alquilado. ¡Se dio!"
        elif porcentaje >= 70:
            mensaje= "¡Upa! Aquí hay fuego y no del de prender el cigarrillo. Ya huelo el chisme desde acá."
        elif porcentaje >= 60:
            mensaje= "Si se toman dos polas encima, coronan. Sobrios no respondemos."
        elif porcentaje >= 50:
            mensaje= "50% ganas de besarse, 50% ganas de meterse un tramacazo. En la mitad está el sabor."
        elif porcentaje >= 45:
            mensaje= "No es el amor de tu vida, pero para pasar el aburrimiento y no morir solo, aguanta."
        elif porcentaje >= 35:
            mensaje= "Compatibilidad estable... pero para armar un caso en **Caso Cerrado**. Mucho tóxico junto."
        elif porcentaje >= 28:
            mensaje= "Sirve para un veneco (un ratico) y ya. Si pasa de las dos horas, terminan en el CAI."
        elif porcentaje >= 20:
            mensaje= "Esto tiene menos futuro que un billete de monopolio. Aléjense por el bien de la salud mental del servidor."
        elif porcentaje >= 12:
            mensaje= "Tienen más química el cloro y el desodorante de piso. Escondan los cuchillos si se van a ver."
        elif porcentaje >= 5:
            mensaje= "Compatibilidad más baja que mi saldo en la cuenta. Se miran y se pegan."
        else:
            mensaje= "Ni el agua y el aceite se atrevieron a tanto. Si se cruzan en la calle, es para darse puño."

        embed= discord.Embed(
            title="💘 Compatibilidad",
            description=f"{usuario1.mention} + {usuario2.mention}",
            color=discord.Color.magenta()
        )
        embed.add_field(name="Resultado", value=f"**{porcentaje}%**\n{mensaje}", inline=False)
        embed.set_footer(text="Sandrone bot - Ideado por @serann0255")
        await interaction.response.send_message(embed=embed)

































        
async def setup(bot):
    await bot.add_cog(Miscelaneo(bot))




#@bot.tree.command(name="suma", description="Suma 2 numeros (Tampoco se pasen de rosca ksjdskd)")
#async def suma(interaction: discord.Interaction, numero1: float, numero2: float):
#    resultado = numero1 + numero2
#    await interaction.response.send_message(f'La suma de **{numero1}** + **{numero2}** es: **{resultado}**')
