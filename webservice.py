import os

from aiohttp import web


async def inicio(request):
    return web.Response(
        text="🎵 Split Music está online"
    )


async def health(request):
    return web.json_response(
        {
            "status": "online",
            "bot": "Split Music"
        }
    )


async def iniciar_webservice():
    app = web.Application()

    app.router.add_get("/", inicio)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(
        os.getenv("PORT", "10000")
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(
        f"🌐 Web Service iniciado en puerto {port}"
    )