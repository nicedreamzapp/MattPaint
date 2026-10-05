"""Open the MattPaint window on screen with a blank canvas (no painting), for the Moonstone chat.
Matt 2026-10-05: the window should be up the moment he opens the chat, and the first thing painted
should be what he asked for, not a stand-in landscape."""
import asyncio, time, urllib.request
from engine import Browser, launch_brave, paint_url

async def main():
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    if not up: await tab.goto(paint_url() + ("&" if "?" in paint_url() else "?") + "r=" + str(int(time.time())))
    await br.close()

asyncio.run(main())
