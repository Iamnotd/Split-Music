import os

import discord
from discord.ext import commands


# =========================================================
# CONFIGURACIÓN
# =========================================================

intents = discord.Intents.default()
intents.message_content = True


class SplitMusicBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="$",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        print("Cargando módulos...")

        # Cargar comandos generales
        await self.load_extension(
            "cogs.general"
        )

        print("✅ General cargado")

        # Cargar comandos de música
        await self.load_extension(
            "cogs.music"
        )

        print("✅ Music cargado")

        # Sincronizar Slash Commands
        try:
            synced = await self.tree.sync()

            print(
                f"✅ Slash commands sincronizados: "
                f"{len(synced)}"
            )

        except Exception as e:
            print(
                f"❌ Error sincronizando "
                f"slash commands: {e}"
            )


# =========================================================
# CREAR BOT
# =========================================================

bot = SplitMusicBot()


# =========================================================
# EVENTO READY
# =========================================================

@bot.event
async def on_ready():
    print()
    print(
        "================================"
    )

    print(
        f"🎵 Split Music conectado como "
        f"{bot.user}"
    )

    print(
        f"🆔 ID: {bot.user.id}"
    )

    print(
        f"🌐 Servidores: {len(bot.guilds)}"
    )

    print(
        "================================"
    )

    print(
        "Comandos $ cargados:"
    )

    for comando in bot.commands:
        print(
            f" - ${comando.name}"
        )

    print(
        "================================"
    )


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "No se encontró la variable de entorno "
        "DISCORD_TOKEN."
    )


# =========================================================
# INICIAR BOT
# =========================================================

bot.run(
    TOKEN
)