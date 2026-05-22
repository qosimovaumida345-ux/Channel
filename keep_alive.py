"""
Render.com free tier botni uxlatib qo'yadi.
Shu fayl oddiy HTTP server ochib UptimeRobot ping uchun javob beradi.
"""
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot ishlayapti ✅")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
