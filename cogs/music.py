import asyncio
import random

import discord
from discord.ext import commands
from discord import app_commands

from services.youtube import buscar_cancion, actualizar_audio


FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn"
}


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.colas = {}
        self.cancion_actual = {}
        self.volumenes = {}
        self.loops = {}

    # =========================================================
    # DATOS POR SERVIDOR
    # =========================================================

    def obtener_cola(self, guild_id):
        if guild_id not in self.colas:
            self.colas[guild_id] = []

        return self.colas[guild_id]

    def obtener_volumen(self, guild_id):
        if guild_id not in self.volumenes:
            self.volumenes[guild_id] = 0.5

        return self.volumenes[guild_id]

    def obtener_loop(self, guild_id):
        return self.loops.get(
            guild_id,
            False
        )

    # =========================================================
    # REPRODUCTOR
    # =========================================================

    async def reproducir_cancion(
        self,
        guild,
        cancion,
        canal_texto
    ):
        guild_id = guild.id
        voice = guild.voice_client

        if voice is None:
            return

        try:
            cancion = await actualizar_audio(
                cancion
            )

            self.cancion_actual[guild_id] = cancion

            audio = discord.FFmpegPCMAudio(
                cancion["url_audio"],
                **FFMPEG_OPTIONS
            )

            source = discord.PCMVolumeTransformer(
                audio,
                volume=self.obtener_volumen(
                    guild_id
                )
            )

            def siguiente(error):
                if error:
                    print(
                        f"Error de reproducción: {error}"
                    )

                asyncio.run_coroutine_threadsafe(
                    self.manejar_fin_cancion(
                        guild,
                        cancion,
                        canal_texto
                    ),
                    self.bot.loop
                )

            voice.play(
                source,
                after=siguiente
            )

            duracion = cancion.get(
                "duracion",
                0
            ) or 0

            minutos = duracion // 60
            segundos = duracion % 60

            volumen = round(
                self.obtener_volumen(guild_id)
                * 100
            )

            embed = discord.Embed(
                title="🎵 Reproduciendo ahora",
                description=(
                    f"**{cancion['titulo']}**"
                ),
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="🎤 Artista / Canal",
                value=cancion["artista"],
                inline=True
            )

            embed.add_field(
                name="⏱️ Duración",
                value=(
                    f"{minutos}:{segundos:02d}"
                ),
                inline=True
            )

            embed.add_field(
                name="🔊 Volumen",
                value=f"{volumen}%",
                inline=True
            )

            if self.obtener_loop(guild_id):
                embed.add_field(
                    name="🔁 Loop",
                    value="Activado",
                    inline=True
                )

            await canal_texto.send(
                embed=embed
            )

        except Exception as e:
            print(
                f"Error reproduciendo canción: {e}"
            )

            await canal_texto.send(
                "❌ No pude reproducir esa canción."
            )

            await self.reproducir_siguiente(
                guild,
                canal_texto
            )

    async def manejar_fin_cancion(
        self,
        guild,
        cancion,
        canal_texto
    ):
        guild_id = guild.id

        if guild.voice_client is None:
            return

        if self.obtener_loop(guild_id):
            await self.reproducir_cancion(
                guild,
                cancion,
                canal_texto
            )
            return

        await self.reproducir_siguiente(
            guild,
            canal_texto
        )

    async def reproducir_siguiente(
        self,
        guild,
        canal_texto
    ):
        guild_id = guild.id
        cola = self.obtener_cola(
            guild_id
        )

        if not cola:
            self.cancion_actual.pop(
                guild_id,
                None
            )
            return

        cancion = cola.pop(0)

        await self.reproducir_cancion(
            guild,
            cancion,
            canal_texto
        )

    # =========================================================
    # COMANDOS $
    # =========================================================

    @commands.command()
    async def entrar(self, ctx):
        if ctx.author.voice is None:
            await ctx.send(
                "❌ Primero debes entrar a un canal de voz."
            )
            return

        canal = ctx.author.voice.channel

        if ctx.voice_client is None:
            await canal.connect()

            await ctx.send(
                f"🎵 Me conecté a **{canal.name}**"
            )

        elif ctx.voice_client.channel != canal:
            await ctx.voice_client.move_to(
                canal
            )

            await ctx.send(
                f"🔊 Me moví a **{canal.name}**"
            )

        else:
            await ctx.send(
                "⚠️ Ya estoy conectado a tu canal."
            )

    @commands.command()
    async def salir(self, ctx):
        if ctx.voice_client is None:
            await ctx.send(
                "❌ No estoy conectado."
            )
            return

        guild_id = ctx.guild.id

        self.colas[guild_id] = []

        self.cancion_actual.pop(
            guild_id,
            None
        )

        self.loops[guild_id] = False

        await ctx.voice_client.disconnect()

        await ctx.send(
            "👋 Salí del canal de voz."
        )

    @commands.command()
    async def play(
        self,
        ctx,
        *,
        busqueda
    ):
        if ctx.author.voice is None:
            await ctx.send(
                "❌ Primero debes entrar a un canal de voz."
            )
            return

        canal = ctx.author.voice.channel

        if ctx.voice_client is None:
            await canal.connect()

        elif ctx.voice_client.channel != canal:
            await ctx.voice_client.move_to(
                canal
            )

        mensaje = await ctx.send(
            f"🔎 Buscando **{busqueda}**..."
        )

        try:
            cancion = await buscar_cancion(
                busqueda
            )

            if cancion is None:
                await mensaje.edit(
                    content=(
                        "❌ No encontré esa canción."
                    )
                )
                return

            cola = self.obtener_cola(
                ctx.guild.id
            )

            cola.append(
                cancion
            )

            if (
                not ctx.voice_client.is_playing()
                and
                not ctx.voice_client.is_paused()
            ):
                await mensaje.edit(
                    content=(
                        f"🎵 Preparando "
                        f"**{cancion['titulo']}**..."
                    )
                )

                await self.reproducir_siguiente(
                    ctx.guild,
                    ctx.channel
                )

            else:
                await mensaje.edit(
                    content=(
                        f"✅ **{cancion['titulo']}** "
                        f"agregada a la cola.\n"
                        f"📋 Posición: "
                        f"**{len(cola)}**"
                    )
                )

        except Exception as e:
            print(
                f"Error en $play: {e}"
            )

            await mensaje.edit(
                content=(
                    "❌ Ocurrió un error "
                    "buscando la canción."
                )
            )

    @play.error
    async def play_error(
        self,
        ctx,
        error
    ):
        if isinstance(
            error,
            commands.MissingRequiredArgument
        ):
            await ctx.send(
                "❌ Debes escribir una canción.\n"
                "Ejemplo: "
                "`$play Starboy The Weeknd`"
            )

    @commands.command()
    async def pause(self, ctx):
        voice = ctx.voice_client

        if voice and voice.is_playing():
            voice.pause()

            await ctx.send(
                "⏸️ Música pausada."
            )

        else:
            await ctx.send(
                "❌ No hay música reproduciéndose."
            )

    @commands.command()
    async def resume(self, ctx):
        voice = ctx.voice_client

        if voice and voice.is_paused():
            voice.resume()

            await ctx.send(
                "▶️ Música reanudada."
            )

        else:
            await ctx.send(
                "❌ No hay música pausada."
            )

    @commands.command()
    async def skip(self, ctx):
        voice = ctx.voice_client

        if voice and (
            voice.is_playing()
            or voice.is_paused()
        ):
            self.loops[
                ctx.guild.id
            ] = False

            voice.stop()

            await ctx.send(
                "⏭️ Canción saltada."
            )

        else:
            await ctx.send(
                "❌ No hay canción para saltar."
            )

    @commands.command()
    async def stop(self, ctx):
        voice = ctx.voice_client

        if voice is None:
            await ctx.send(
                "❌ No estoy conectado."
            )
            return

        guild_id = ctx.guild.id

        self.colas[guild_id] = []
        self.loops[guild_id] = False

        self.cancion_actual.pop(
            guild_id,
            None
        )

        if (
            voice.is_playing()
            or voice.is_paused()
        ):
            voice.stop()

        await ctx.send(
            "⏹️ Música detenida.\n"
            "🗑️ Cola eliminada."
        )

    @commands.command()
    async def volume(
        self,
        ctx,
        volumen: int
    ):
        if volumen < 0 or volumen > 100:
            await ctx.send(
                "❌ El volumen debe estar "
                "entre 0 y 100."
            )
            return

        guild_id = ctx.guild.id

        self.volumenes[guild_id] = (
            volumen / 100
        )

        voice = ctx.voice_client

        if (
            voice
            and voice.source
            and isinstance(
                voice.source,
                discord.PCMVolumeTransformer
            )
        ):
            voice.source.volume = (
                volumen / 100
            )

        await ctx.send(
            f"🔊 Volumen: **{volumen}%**"
        )

    @volume.error
    async def volume_error(
        self,
        ctx,
        error
    ):
        await ctx.send(
            "❌ Usa `$volume` seguido "
            "de un número del 0 al 100.\n"
            "Ejemplo: `$volume 50`"
        )

    @commands.command()
    async def loop(self, ctx):
        guild_id = ctx.guild.id

        if guild_id not in self.cancion_actual:
            await ctx.send(
                "❌ No hay canción "
                "reproduciéndose."
            )
            return

        self.loops[guild_id] = (
            not self.obtener_loop(guild_id)
        )

        if self.loops[guild_id]:
            await ctx.send(
                "🔁 Loop **activado**."
            )

        else:
            await ctx.send(
                "➡️ Loop **desactivado**."
            )

    @commands.command()
    async def shuffle(self, ctx):
        cola = self.obtener_cola(
            ctx.guild.id
        )

        if len(cola) < 2:
            await ctx.send(
                "❌ Necesitas al menos "
                "2 canciones en la cola."
            )
            return

        random.shuffle(
            cola
        )

        await ctx.send(
            "🔀 Cola mezclada."
        )

    @commands.command()
    async def remove(
        self,
        ctx,
        posicion: int
    ):
        cola = self.obtener_cola(
            ctx.guild.id
        )

        if (
            posicion < 1
            or posicion > len(cola)
        ):
            await ctx.send(
                "❌ Esa posición no existe."
            )
            return

        cancion = cola.pop(
            posicion - 1
        )

        await ctx.send(
            f"🗑️ **{cancion['titulo']}** eliminada."
        )

    @remove.error
    async def remove_error(
        self,
        ctx,
        error
    ):
        await ctx.send(
            "❌ Usa `$remove` seguido "
            "de la posición.\n"
            "Ejemplo: `$remove 2`"
        )

    @commands.command()
    async def clear(self, ctx):
        cola = self.obtener_cola(
            ctx.guild.id
        )

        cola.clear()

        await ctx.send(
            "🗑️ Cola eliminada."
        )

    @commands.command(name="queue")
    async def mostrar_cola(
        self,
        ctx
    ):
        guild_id = ctx.guild.id

        cola = self.obtener_cola(
            guild_id
        )

        actual = self.cancion_actual.get(
            guild_id
        )

        if not actual and not cola:
            await ctx.send(
                "📭 La cola está vacía."
            )
            return

        embed = discord.Embed(
            title="🎶 Cola de reproducción",
            color=discord.Color.blurple()
        )

        if actual:
            embed.add_field(
                name="🎧 Reproduciendo",
                value=actual["titulo"],
                inline=False
            )

        if cola:
            texto = ""

            for numero, cancion in enumerate(
                cola[:10],
                start=1
            ):
                texto += (
                    f"`{numero}.` "
                    f"{cancion['titulo']}\n"
                )

            embed.add_field(
                name="📋 Siguientes",
                value=texto,
                inline=False
            )

        await ctx.send(
            embed=embed
        )

    @commands.command()
    async def nowplaying(
        self,
        ctx
    ):
        cancion = self.cancion_actual.get(
            ctx.guild.id
        )

        if cancion is None:
            await ctx.send(
                "❌ No hay canción "
                "reproduciéndose."
            )
            return

        await ctx.send(
            f"🎧 Sonando ahora: "
            f"**{cancion['titulo']}**"
        )

    # =========================================================
    # SLASH COMMANDS /
    # =========================================================

    @app_commands.command(
        name="play",
        description="Reproduce una canción"
    )
    @app_commands.describe(
        cancion="Nombre de la canción"
    )
    async def slash_play(
        self,
        interaction: discord.Interaction,
        cancion: str
    ):
        if (
            interaction.guild is None
            or interaction.user.voice is None
        ):
            await interaction.response.send_message(
                "❌ Primero debes entrar "
                "a un canal de voz.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        canal = interaction.user.voice.channel
        voice = interaction.guild.voice_client

        if voice is None:
            voice = await canal.connect()

        elif voice.channel != canal:
            await voice.move_to(
                canal
            )

        try:
            resultado = await buscar_cancion(
                cancion
            )

            if resultado is None:
                await interaction.followup.send(
                    "❌ No encontré esa canción."
                )
                return

            cola = self.obtener_cola(
                interaction.guild.id
            )

            cola.append(
                resultado
            )

            if (
                not voice.is_playing()
                and not voice.is_paused()
            ):
                await interaction.followup.send(
                    f"🎵 Preparando "
                    f"**{resultado['titulo']}**..."
                )

                await self.reproducir_siguiente(
                    interaction.guild,
                    interaction.channel
                )

            else:
                await interaction.followup.send(
                    f"✅ **{resultado['titulo']}** "
                    f"agregada a la cola.\n"
                    f"📋 Posición: "
                    f"**{len(cola)}**"
                )

        except Exception as e:
            print(
                f"Error en /play: {e}"
            )

            await interaction.followup.send(
                "❌ Ocurrió un error "
                "buscando la canción."
            )

    @app_commands.command(
        name="pause",
        description="Pausa la canción"
    )
    async def slash_pause(
        self,
        interaction: discord.Interaction
    ):
        voice = (
            interaction.guild.voice_client
            if interaction.guild
            else None
        )

        if voice and voice.is_playing():
            voice.pause()

            await interaction.response.send_message(
                "⏸️ Música pausada."
            )

        else:
            await interaction.response.send_message(
                "❌ No hay música reproduciéndose.",
                ephemeral=True
            )

    @app_commands.command(
        name="resume",
        description="Continúa la canción"
    )
    async def slash_resume(
        self,
        interaction: discord.Interaction
    ):
        voice = (
            interaction.guild.voice_client
            if interaction.guild
            else None
        )

        if voice and voice.is_paused():
            voice.resume()

            await interaction.response.send_message(
                "▶️ Música reanudada."
            )

        else:
            await interaction.response.send_message(
                "❌ No hay música pausada.",
                ephemeral=True
            )

    @app_commands.command(
        name="skip",
        description="Salta la canción actual"
    )
    async def slash_skip(
        self,
        interaction: discord.Interaction
    ):
        voice = (
            interaction.guild.voice_client
            if interaction.guild
            else None
        )

        if voice and (
            voice.is_playing()
            or voice.is_paused()
        ):
            self.loops[
                interaction.guild.id
            ] = False

            voice.stop()

            await interaction.response.send_message(
                "⏭️ Canción saltada."
            )

        else:
            await interaction.response.send_message(
                "❌ No hay canción para saltar.",
                ephemeral=True
            )

    @app_commands.command(
        name="stop",
        description="Detiene la música y limpia la cola"
    )
    async def slash_stop(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if voice is None:
            await interaction.response.send_message(
                "❌ No estoy conectado.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        self.colas[guild_id] = []
        self.loops[guild_id] = False

        self.cancion_actual.pop(
            guild_id,
            None
        )

        if (
            voice.is_playing()
            or voice.is_paused()
        ):
            voice.stop()

        await interaction.response.send_message(
            "⏹️ Música detenida y cola eliminada."
        )

    @app_commands.command(
        name="volume",
        description="Cambia el volumen"
    )
    @app_commands.describe(
        cantidad="Volumen entre 0 y 100"
    )
    async def slash_volume(
        self,
        interaction: discord.Interaction,
        cantidad: app_commands.Range[
            int,
            0,
            100
        ]
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        self.volumenes[guild_id] = (
            cantidad / 100
        )

        voice = interaction.guild.voice_client

        if (
            voice
            and voice.source
            and isinstance(
                voice.source,
                discord.PCMVolumeTransformer
            )
        ):
            voice.source.volume = (
                cantidad / 100
            )

        await interaction.response.send_message(
            f"🔊 Volumen: **{cantidad}%**"
        )

    @app_commands.command(
        name="loop",
        description="Activa o desactiva el loop"
    )
    async def slash_loop(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        if guild_id not in self.cancion_actual:
            await interaction.response.send_message(
                "❌ No hay canción reproduciéndose.",
                ephemeral=True
            )
            return

        self.loops[guild_id] = (
            not self.obtener_loop(guild_id)
        )

        if self.loops[guild_id]:
            mensaje = "🔁 Loop **activado**."
        else:
            mensaje = "➡️ Loop **desactivado**."

        await interaction.response.send_message(
            mensaje
        )

    @app_commands.command(
        name="queue",
        description="Muestra la cola"
    )
    async def slash_queue(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        cola = self.obtener_cola(
            guild_id
        )

        actual = self.cancion_actual.get(
            guild_id
        )

        if not actual and not cola:
            await interaction.response.send_message(
                "📭 La cola está vacía.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎶 Cola de reproducción",
            color=discord.Color.blurple()
        )

        if actual:
            embed.add_field(
                name="🎧 Reproduciendo",
                value=actual["titulo"],
                inline=False
            )

        if cola:
            texto = ""

            for numero, cancion in enumerate(
                cola[:10],
                start=1
            ):
                texto += (
                    f"`{numero}.` "
                    f"{cancion['titulo']}\n"
                )

            embed.add_field(
                name="📋 Siguientes",
                value=texto,
                inline=False
            )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="shuffle",
        description="Mezcla la cola"
    )
    async def slash_shuffle(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        cola = self.obtener_cola(
            interaction.guild.id
        )

        if len(cola) < 2:
            await interaction.response.send_message(
                "❌ Necesitas al menos "
                "2 canciones en la cola.",
                ephemeral=True
            )
            return

        random.shuffle(
            cola
        )

        await interaction.response.send_message(
            "🔀 Cola mezclada."
        )

    @app_commands.command(
        name="clear",
        description="Vacía la cola"
    )
    async def slash_clear(
        self,
        interaction: discord.Interaction
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando debe usarse "
                "en un servidor.",
                ephemeral=True
            )
            return

        cola = self.obtener_cola(
            interaction.guild.id
        )

        cola.clear()

        await interaction.response.send_message(
            "🗑️ Cola eliminada."
        )


async def setup(bot):
    await bot.add_cog(
        Music(bot)
    )