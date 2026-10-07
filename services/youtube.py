import asyncio
import yt_dlp


YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": False
}


async def buscar_cancion(busqueda: str):
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


async def actualizar_audio(cancion: dict):
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