import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# ID de tu servidor — sync instantaneo para desarrollo
GUILD_ID = 1348824425377697792

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="s!", intents=intents) #Prefijo solo pq si

@bot.event
async def on_ready():
    print(f'{bot.user} se ha conectado correctamente al servidor!')
    await bot.change_presence(
        activity=discord.Game(name="COLUMBINA!!"),
        status=discord.Status.online
    )

#Funcion para llamar todas las categorias "cogs"
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"cargado: {filename}")

@bot.event
async def setup_hook():
    await load_cogs()

    guild = discord.Object(id=GUILD_ID)
    # Copia todos los comandos globales al servidor y sincroniza al instante
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f'Se han sincronizado {len(synced)} comandos en el servidor (instantaneo)')
#========================= Comandos de admin =========================
@bot.command()
@commands.is_owner()
async def reload(ctx, cog: str = None):
    """Recarga un cog o todos si no se especifica ninguno. Uso: s!reload miscelaneo"""
    guild = discord.Object(id=GUILD_ID)
    try:
        if cog:
            ext = f"cogs.{cog}"
            if ext in bot.extensions:
                await bot.reload_extension(ext)
            else:
                await bot.load_extension(ext)  # Cog nuevo, nunca habia sido cargado
            print(f"Recargado: {cog}")
        else:
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and filename != "__init__.py":
                    ext = f"cogs.{filename[:-3]}"
                    if ext in bot.extensions:
                        await bot.reload_extension(ext)
                    else:
                        await bot.load_extension(ext)
                    print(f"Recargado: {filename}")

        # Sincroniza los nuevos comandos al servidor al instante
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        await ctx.send(f"✅ Recargado y sincronizados {len(synced)} comandos.")
    except Exception as e:
        await ctx.send(f"❌ Error al recargar: `{e}`")

bot.run(os.getenv("TOKEN"))

