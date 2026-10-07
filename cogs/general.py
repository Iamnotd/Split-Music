import discord
from discord.ext import commands
from discord import app_commands


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # $PING
    # =========================================================

    @commands.command(name="ping")
    async def ping(self, ctx):
        latencia = round(
            self.bot.latency * 1000
        )

        await ctx.send(
            f"🏓 Pong! `{latencia} ms`"
        )

    # =========================================================
    # $HOLA
    # =========================================================

    @commands.command(name="hola")
    async def hola(self, ctx):
        await ctx.send(
            f"👋 ¡Hola {ctx.author.mention}!"
        )

    # =========================================================
    # $HELP
    # =========================================================

    @commands.command(name="help")
    async def ayuda(self, ctx):
        embed = discord.Embed(
            title="🎵 Split Music",
            description=(
                "Comandos disponibles.\n"
                "Puedes utilizar `$` o los comandos `/`."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎵 Reproducción",
            value=(
                "`$play canción`\n"
                "`$pause`\n"
                "`$resume`\n"
                "`$skip`\n"
                "`$stop`\n"
                "`$nowplaying`"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Cola",
            value=(
                "`$queue`\n"
                "`$shuffle`\n"
                "`$remove 2`\n"
                "`$clear`"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Configuración",
            value=(
                "`$volume 50`\n"
                "`$loop`\n"
                "`$entrar`\n"
                "`$salir`"
            ),
            inline=False
        )

        embed.add_field(
            name="⚡ Slash Commands",
            value=(
                "`/play`\n"
                "`/pause`\n"
                "`/resume`\n"
                "`/skip`\n"
                "`/stop`\n"
                "`/volume`\n"
                "`/loop`\n"
                "`/queue`\n"
                "`/shuffle`\n"
                "`/clear`\n"
                "`/ping`"
            ),
            inline=False
        )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # /PING
    # =========================================================

    @app_commands.command(
        name="ping",
        description="Muestra la latencia de Split Music"
    )
    async def slash_ping(
        self,
        interaction: discord.Interaction
    ):
        latencia = round(
            self.bot.latency * 1000
        )

        await interaction.response.send_message(
            f"🏓 Pong! `{latencia} ms`"
        )


async def setup(bot):
    await bot.add_cog(
        General(bot)
    )