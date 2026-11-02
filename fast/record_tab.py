"""record_tab — records the MattPaint window (the paint tab on CDP 9231) while it paints, for the explainer video.

Matt 2026-11-02: "I want the MattPaint record and sped up so people can see it". Records the tab itself
through the browser's screencast (no screen recording, so other windows and notifications never get in),
saves every frame with its real time, and on stop writes a real-time mp4 that can be sped up in the edit.

    record_tab.py OUT_DIR            # runs until OUT_DIR/stop exists (or Ctrl-C), then writes OUT_DIR/recording.mp4
"""
import asyncio, base64, json, os, signal, subprocess, sys, time, urllib.request
import websockets

PORT = 9231


async def main(out):
    os.makedirs(os.path.join(out, "f"), exist_ok=True)
    url = json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json/version"))["webSocketDebuggerUrl"]
    ws = await websockets.connect(url, max_size=128 * 1024 * 1024, ping_interval=None)
    mid = 0
    async def send(method, params=None, session=None):
        nonlocal mid; mid += 1
        m = {"id": mid, "method": method, "params": params or {}}
        if session: m["sessionId"] = session
        await ws.send(json.dumps(m)); return mid
    await send("Target.getTargets")
    targets = None
    while targets is None:
        m = json.loads(await ws.recv())
        if m.get("id") == 1: targets = [t for t in m["result"]["targetInfos"] if t["type"] == "page"]
    tgt = targets[0]["targetId"]                       # the same tab the painters use (engine.existing_page)
    await send("Target.attachToTarget", {"targetId": tgt, "flatten": True})
    session = None
    while session is None:
        m = json.loads(await ws.recv())
        if m.get("id") == 2: session = m["result"]["sessionId"]
    await send("Page.enable", session=session)
    await send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": 1920, "maxHeight": 1200,
                                        "everyNthFrame": 1}, session=session)
    stop = os.path.join(out, "stop"); times = []; n = 0
    print(f"recording tab {tgt[:8]} -> {out}", flush=True)
    while not os.path.exists(stop):
        try:
            m = json.loads(await asyncio.wait_for(ws.recv(), 1.0))
        except asyncio.TimeoutError:
            continue
        if m.get("method") == "Page.screencastFrame":
            p = m["params"]
            open(os.path.join(out, "f", f"{n:06d}.jpg"), "wb").write(base64.b64decode(p["data"]))
            times.append(time.time()); n += 1
            await send("Page.screencastFrameAck", {"sessionId": p["sessionId"]}, session=session)
    await send("Page.stopScreencast", session=session); await ws.close()
    # concat list with the real gap between frames, so the mp4 plays in real time
    with open(os.path.join(out, "list.txt"), "w") as f:
        for i in range(n):
            d = (times[i + 1] - times[i]) if i + 1 < n else 0.1
            f.write(f"file 'f/{i:06d}.jpg'\nduration {max(d, 0.001):.4f}\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
                    "-vf", "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-c:v", "libx264", "-crf", "18",
                    "recording.mp4"], cwd=out, check=True)
    print(f"{n} frames over {times[-1] - times[0]:.0f}s -> {out}/recording.mp4" if n else "no frames", flush=True)


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    signal.signal(signal.SIGTERM, lambda *a: open(os.path.join(out, "stop"), "w").close())
    asyncio.run(main(out))
