import asyncio
import random

import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp

import config


# =========================================================
# CONFIGURACIÓN
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="$",
    intents=intents,
    help_command=None
)


YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": False
}


FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn"
}


# =========================================================
# DATOS POR SERVIDOR
# =========================================================

colas = {}
cancion_actual = {}
volumenes = {}
loops = {}


def obtener_cola(guild_id):
    if guild_id not in colas:
        colas[guild_id] = []

    return colas[guild_id]


def obtener_volumen(guild_id):
    if guild_id not in volumenes:
        volumenes[guild_id] = 0.5

    return volumenes[guild_id]


def obtener_loop(guild_id):
    return loops.get(guild_id, False)


# =========================================================
# YOUTUBE
# =========================================================

async def buscar_cancion(busqueda):

    loop = asyncio.get_running_loop()

    def buscar():

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:

            info = ydl.extract_info(
                f"ytsearch1:{busqueda}",
                download=False
            )

            if "entries" in info:

                if not info["entries"]:
                    return None

                info = info["entries"][0]

            return {
                "titulo": info.get(
                    "title",
                    "Canción desconocida"
                ),

                "artista": info.get(
                    "uploader",
                    "Desconocido"
                ),

                "duracion": info.get(
                    "duration",
                    0
                ),

                "url_audio": info["url"],

                "webpage_url": info.get(
                    "webpage_url",
                    ""
                )
            }

    return await loop.run_in_executor(
        None,
        buscar
    )


async def actualizar_audio(cancion):

    if not cancion.get("webpage_url"):
        return cancion

    loop = asyncio.get_running_loop()

    def actualizar():

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:

            info = ydl.extract_info(
                cancion["webpage_url"],
                download=False
            )

            cancion["url_audio"] = info["url"]

            return cancion

    try:

        return await loop.run_in_executor(
            None,
            actualizar
        )

    except Exception as e:

        print(
            f"Error actualizando URL: {e}"
        )

        return cancion


# =========================================================
# REPRODUCTOR
# =========================================================

async def reproducir_cancion(
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

        cancion_actual[guild_id] = cancion

        audio = discord.FFmpegPCMAudio(
            cancion["url_audio"],
            **FFMPEG_OPTIONS
        )

        source = discord.PCMVolumeTransformer(
            audio,
            volume=obtener_volumen(
                guild_id
            )
        )

        def siguiente(error):

            if error:
                print(
                    f"Error de reproducción: {error}"
                )

            asyncio.run_coroutine_threadsafe(
                manejar_fin_cancion(
                    guild,
                    cancion,
                    canal_texto
                ),
                bot.loop
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
            obtener_volumen(guild_id)
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

        if obtener_loop(guild_id):

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

        await reproducir_siguiente(
            guild,
            canal_texto
        )


async def manejar_fin_cancion(
    guild,
    cancion,
    canal_texto
):

    guild_id = guild.id

    if guild.voice_client is None:
        return

    if obtener_loop(guild_id):

        await reproducir_cancion(
            guild,
            cancion,
            canal_texto
        )

        return

    await reproducir_siguiente(
        guild,
        canal_texto
    )


async def reproducir_siguiente(
    guild,
    canal_texto
):

    guild_id = guild.id

    cola = obtener_cola(
        guild_id
    )

    if not cola:

        cancion_actual.pop(
            guild_id,
            None
        )

        return

    cancion = cola.pop(0)

    await reproducir_cancion(
        guild,
        cancion,
        canal_texto
    )


# =========================================================
# EVENTO READY
# =========================================================

@bot.event
async def on_ready():

    print()
    print(
        f"Bot conectado como {bot.user}"
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"Slash commands sincronizados: "
            f"{len(synced)}"
        )

    except Exception as e:

        print(
            f"Error sincronizando "
            f"slash commands: {e}"
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
# COMANDOS $
# =========================================================


# -------------------------
# PING
# -------------------------

@bot.command()
async def ping(ctx):

    latencia = round(
        bot.latency * 1000
    )

    await ctx.send(
        f"🏓 Pong! `{latencia} ms`"
    )


# -------------------------
# HOLA
# -------------------------

@bot.command()
async def hola(ctx):

    await ctx.send(
        f"👋 ¡Hola {ctx.author.mention}!"
    )


# -------------------------
# ENTRAR
# -------------------------

@bot.command()
async def entrar(ctx):

    if ctx.author.voice is None:

        await ctx.send(
            "❌ Primero debes entrar "
            "a un canal de voz."
        )

        return

    canal = ctx.author.voice.channel

    if ctx.voice_client is None:

        await canal.connect()

        await ctx.send(
            f"🎵 Me conecté a "
            f"**{canal.name}**"
        )

    elif ctx.voice_client.channel != canal:

        await ctx.voice_client.move_to(
            canal
        )

        await ctx.send(
            f"🔊 Me moví a "
            f"**{canal.name}**"
        )

    else:

        await ctx.send(
            "⚠️ Ya estoy conectado "
            "a tu canal."
        )


# -------------------------
# SALIR
# -------------------------

@bot.command()
async def salir(ctx):

    if ctx.voice_client is None:

        await ctx.send(
            "❌ No estoy conectado."
        )

        return

    guild_id = ctx.guild.id

    colas[guild_id] = []

    cancion_actual.pop(
        guild_id,
        None
    )

    loops[guild_id] = False

    await ctx.voice_client.disconnect()

    await ctx.send(
        "👋 Salí del canal de voz."
    )


# -------------------------
# PLAY
# -------------------------

@bot.command()
async def play(ctx, *, busqueda):

    if ctx.author.voice is None:

        await ctx.send(
            "❌ Primero debes entrar "
            "a un canal de voz."
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
        f"🔎 Buscando "
        f"**{busqueda}**..."
    )

    try:

        cancion = await buscar_cancion(
            busqueda
        )

        if cancion is None:

            await mensaje.edit(
                content=(
                    "❌ No encontré "
                    "esa canción."
                )
            )

            return

        cola = obtener_cola(
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

            await reproducir_siguiente(
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


# -------------------------
# PAUSE
# -------------------------

@bot.command()
async def pause(ctx):

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


# -------------------------
# RESUME
# -------------------------

@bot.command()
async def resume(ctx):

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


# -------------------------
# SKIP
# -------------------------

@bot.command()
async def skip(ctx):

    voice = ctx.voice_client

    if voice and (
        voice.is_playing()
        or voice.is_paused()
    ):

        loops[
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


# -------------------------
# STOP
# -------------------------

@bot.command()
async def stop(ctx):

    voice = ctx.voice_client

    if voice is None:

        await ctx.send(
            "❌ No estoy conectado."
        )

        return

    guild_id = ctx.guild.id

    colas[guild_id] = []

    loops[guild_id] = False

    cancion_actual.pop(
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


# -------------------------
# VOLUME
# -------------------------

@bot.command()
async def volume(
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

    volumenes[guild_id] = (
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


# -------------------------
# LOOP
# -------------------------

@bot.command()
async def loop(ctx):

    guild_id = ctx.guild.id

    if guild_id not in cancion_actual:

        await ctx.send(
            "❌ No hay canción "
            "reproduciéndose."
        )

        return

    loops[guild_id] = (
        not obtener_loop(guild_id)
    )

    if loops[guild_id]:

        await ctx.send(
            "🔁 Loop **activado**."
        )

    else:

        await ctx.send(
            "➡️ Loop **desactivado**."
        )


# -------------------------
# SHUFFLE
# -------------------------

@bot.command()
async def shuffle(ctx):

    cola = obtener_cola(
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


# -------------------------
# REMOVE
# -------------------------

@bot.command()
async def remove(
    ctx,
    posicion: int
):

    cola = obtener_cola(
        ctx.guild.id
    )

    if (
        posicion < 1
        or posicion > len(cola)
    ):

        await ctx.send(
            "❌ Esa posición "
            "no existe."
        )

        return

    cancion = cola.pop(
        posicion - 1
    )

    await ctx.send(
        f"🗑️ **{cancion['titulo']}** "
        f"eliminada."
    )


# -------------------------
# CLEAR
# -------------------------

@bot.command()
async def clear(ctx):

    cola = obtener_cola(
        ctx.guild.id
    )

    cola.clear()

    await ctx.send(
        "🗑️ Cola eliminada."
    )


# -------------------------
# QUEUE
# -------------------------

@bot.command(name="queue")
async def mostrar_cola(ctx):

    guild_id = ctx.guild.id

    cola = obtener_cola(
        guild_id
    )

    actual = cancion_actual.get(
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


# -------------------------
# NOWPLAYING
# -------------------------

@bot.command()
async def nowplaying(ctx):

    cancion = cancion_actual.get(
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


# -------------------------
# HELP
# -------------------------

@bot.command(name="help")
async def ayuda(ctx):

    embed = discord.Embed(
        title="🎵 Comandos del bot",
        description=(
            "Puedes usar `$` o los nuevos "
            "comandos `/`."
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

    await ctx.send(
        embed=embed
    )


# =========================================================
# SLASH COMMANDS /
# =========================================================


# -------------------------
# /PING
# -------------------------

@bot.tree.command(
    name="ping",
    description="Muestra la latencia del bot"
)
async def slash_ping(
    interaction: discord.Interaction
):

    latencia = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong! `{latencia} ms`"
    )


# -------------------------
# /PLAY
# -------------------------

@bot.tree.command(
    name="play",
    description="Reproduce una canción"
)
@app_commands.describe(
    cancion="Nombre de la canción"
)
async def slash_play(
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

        cola = obtener_cola(
            interaction.guild.id
        )

        cola.append(
            resultado
        )

        if (
            not voice.is_playing()
            and
            not voice.is_paused()
        ):

            await interaction.followup.send(
                f"🎵 Preparando "
                f"**{resultado['titulo']}**..."
            )

            await reproducir_siguiente(
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


# -------------------------
# /PAUSE
# -------------------------

@bot.tree.command(
    name="pause",
    description="Pausa la canción"
)
async def slash_pause(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

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


# -------------------------
# /RESUME
# -------------------------

@bot.tree.command(
    name="resume",
    description="Continúa la canción"
)
async def slash_resume(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

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


# -------------------------
# /SKIP
# -------------------------

@bot.tree.command(
    name="skip",
    description="Salta la canción actual"
)
async def slash_skip(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

    if voice and (
        voice.is_playing()
        or voice.is_paused()
    ):

        loops[
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


# -------------------------
# /STOP
# -------------------------

@bot.tree.command(
    name="stop",
    description="Detiene la música y limpia la cola"
)
async def slash_stop(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

    if voice is None:

        await interaction.response.send_message(
            "❌ No estoy conectado.",
            ephemeral=True
        )

        return

    guild_id = interaction.guild.id

    colas[guild_id] = []
    loops[guild_id] = False

    cancion_actual.pop(
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


# -------------------------
# /VOLUME
# -------------------------

@bot.tree.command(
    name="volume",
    description="Cambia el volumen"
)
@app_commands.describe(
    cantidad="Volumen entre 0 y 100"
)
async def slash_volume(
    interaction: discord.Interaction,
    cantidad: app_commands.Range[
        int,
        0,
        100
    ]
):

    guild_id = interaction.guild.id

    volumenes[guild_id] = (
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


# -------------------------
# /LOOP
# -------------------------

@bot.tree.command(
    name="loop",
    description="Activa o desactiva el loop"
)
async def slash_loop(
    interaction: discord.Interaction
):

    guild_id = interaction.guild.id

    if guild_id not in cancion_actual:

        await interaction.response.send_message(
            "❌ No hay canción reproduciéndose.",
            ephemeral=True
        )

        return

    loops[guild_id] = (
        not obtener_loop(guild_id)
    )

    if loops[guild_id]:

        mensaje = "🔁 Loop **activado**."

    else:

        mensaje = "➡️ Loop **desactivado**."

    await interaction.response.send_message(
        mensaje
    )


# -------------------------
# /QUEUE
# -------------------------

@bot.tree.command(
    name="queue",
    description="Muestra la cola"
)
async def slash_queue(
    interaction: discord.Interaction
):

    guild_id = interaction.guild.id

    cola = obtener_cola(
        guild_id
    )

    actual = cancion_actual.get(
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


# -------------------------
# /SHUFFLE
# -------------------------

@bot.tree.command(
    name="shuffle",
    description="Mezcla la cola"
)
async def slash_shuffle(
    interaction: discord.Interaction
):

    cola = obtener_cola(
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


# -------------------------
# /CLEAR
# -------------------------

@bot.tree.command(
    name="clear",
    description="Vacía la cola"
)
async def slash_clear(
    interaction: discord.Interaction
):

    cola = obtener_cola(
        interaction.guild.id
    )

    cola.clear()

    await interaction.response.send_message(
        "🗑️ Cola eliminada."
    )


# =========================================================
# ERRORES DE COMANDOS $
# =========================================================

@play.error
async def play_error(
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


@volume.error
async def volume_error(
    ctx,
    error
):

    await ctx.send(
        "❌ Usa `$volume` seguido "
        "de un número del 0 al 100.\n"
        "Ejemplo: `$volume 50`"
    )


@remove.error
async def remove_error(
    ctx,
    error
):

    await ctx.send(
        "❌ Usa `$remove` seguido "
        "de la posición.\n"
        "Ejemplo: `$remove 2`"
    )


# =========================================================
# INICIAR
# =========================================================

bot.run(config.TOKEN)