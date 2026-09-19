"""First recipe from a TEXT-ONLY model (mlx_lm) — for models mlx_vlm can't load, e.g. the 4-bit
SuperGemma (no vision weights: "Missing 963 parameters"). Same brief and first ask as director.py.
    text_director.py MODEL NAME "prompt" OUTDIR
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import director as D
from mlx_lm import load, generate
model_id, name, prompt, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
brief = D.Direction.__new__(D.Direction)
D.Direction.__init__(brief, None, prompt[:40].upper(), prompt, out, 0, 0, False)
model, tok = load(model_id)
t = time.time()
note_ = ""
for attempt in range(3):                          # same three tries director.py gives a model
    msgs = [{"role": "user", "content": brief.prefix + "\n" + D.FIRST_ASK + note_}]
    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    text = D.ticking(f"{name} is writing the recipe", generate, model, tok, prompt=p, max_tokens=6000)
    for end in ("</think>", "<channel|>"):
        if end in text:
            text = text.split(end, 1)[1]
    (out / f"r0_director{attempt}.md").write_text(text)
    r, problem = D.extract_json(text)
    if r is not None:
        r, problem = D.validate(r)
    if r is not None:
        break
    print(f"attempt {attempt}: {problem[:160]}", flush=True)
    note_ = f"\n\nYOUR LAST RECIPE FAILED: {problem}\nFix it and reply with the full recipe in one ```json block."
else:
    sys.exit("no paintable recipe after 3 tries")
note = problem
r.setdefault("title", "HAUNTED FOREST")
(out / "r0.json").write_text(json.dumps(r, indent=1))
print(f"recipe in {time.time() - t:.0f}s; note: {note}", flush=True)
