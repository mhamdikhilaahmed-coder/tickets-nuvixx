import os, asyncio
from aiohttp import web

async def handle_root(request):
    return web.Response(text='nuvix tickets connected')

async def handle_health(request):
    return web.Response(text='nuvix tickets connected')

async def run_web_app():
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    port = int(os.getenv('PORT', '10000'))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'Server running on port {port}')
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(run_web_app())
