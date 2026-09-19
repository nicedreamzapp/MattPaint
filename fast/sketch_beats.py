"""Storyboard sketches for Story Forge (2026-09-18): turn scene descriptions into quick MattPaint
paintings, painted live in the MattPaint window, for the story reel's missing shots.

Story Forge's bin/forge-animatic shows a black "MISSING" card for every beat that has no still
yet. This paints a rough sketch of that beat instead, so a film can be watched end to end as
pictures on day one, before any GPU render. A small local model (SuperGemma, text only, no
thinking) writes each recipe; the scene engine paints it. Sketches are cached by beat text, so
re-running the reel costs nothing.

    sketch_beats.py beats.json OUT_DIR          beats.json = ["beat text", ...]
    -> OUT_DIR/sketch_<hash>.png per beat; prints "beat<TAB>path" lines (path empty on failure)
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
MODEL = os.environ.get("SKETCH_MODEL", "DreamFoundries/SuperGemma-4-12b-abliterated-4bit")
WHO = os.environ.get("SKETCH_NAME", "SuperGemma · storyboard sketch")
PAINT_PY = os.path.expanduser("~/.local/mlx-server/bin/python3")
MEM = os.path.expanduser("~/SongForgeM5/mem_client.py")


def key(beat):
    return hashlib.sha1(beat.strip().encode()).hexdigest()[:12]


def main():
    beats = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    todo = [b for b in beats if not (out / f"sketch_{key(b)}.png").is_file()]
    results = {}
    if todo:
        import director as D                        # the recipe brief, validator and first ask
        from mlx_lm import load, generate
        lease = subprocess.run(["/usr/bin/python3", MEM, "wait", "mattpaint-sketch", "10", "--timeout", "300"],
                               capture_output=True, text=True).stdout.split()
        lease = next((w for w in reversed(lease) if w.startswith("L") and "-" in w), "")
        try:
            model, tok = load(MODEL)
            for beat in todo:
                prompt = (f"A storyboard sketch for one scene of an animated film: {beat}. "
                          "Paint the characters and places this scene names, big and clear.")
                brief = D.Direction.__new__(D.Direction)
                D.Direction.__init__(brief, None, "SKETCH", prompt, out, 0, 0, False)
                note, r = "", None
                for attempt in range(3):
                    msgs = [{"role": "user", "content": brief.prefix + "\n" + D.FIRST_ASK + note}]
                    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
                    text = D.ticking(f"sketching: {beat[:40]}", generate, model, tok, prompt=p, max_tokens=5000)
                    for end in ("</think>", "<channel|>"):
                        text = text.split(end, 1)[-1]
                    r, problem = D.extract_json(text)
                    if r is not None:
                        r, problem = D.validate(r)
                    if r is not None:
                        break
                    note = f"\n\nYOUR LAST RECIPE FAILED: {problem}\nFix it and reply with the full recipe in one ```json block."
                if r is None:
                    continue
                r["title"] = "SKETCH — " + beat[:34].upper()
                rp = out / f"sketch_{key(beat)}.json"
                rp.write_text(json.dumps(r, indent=1))
                png = out / f"sketch_{key(beat)}.png"
                env = dict(os.environ, MATTPAINT_NAME=WHO, PAINT_SECONDS="10")
                subprocess.run([PAINT_PY, str(HERE / "scene_engine.py"), str(rp), str(png)],
                               cwd=HERE, env=env, capture_output=True, timeout=300)
        finally:
            if lease:
                subprocess.run(["/usr/bin/python3", MEM, "release", lease], capture_output=True)
    for b in beats:
        png = out / f"sketch_{key(b)}.png"
        print(f"{b}\t{png if png.is_file() else ''}", flush=True)


if __name__ == "__main__":
    main()
