#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build / update a content board page from config.json + data.json (+ images.json).

  python3 inject.py                          build board.html from board_template.html
  python3 inject.py board.html               update an existing page in place (daily sync)
  python3 inject.py board.html --images      ...and refresh the artwork block too
  python3 inject.py --config other.json      use a different brand config
  python3 inject.py --sql                    print the Notion SELECT for this brand

Three data blocks live in the page and are swapped independently:
  board-config  brand / labels / stages / hashtag rules   (changes when config.json changes)
  board-data    rows from Notion                          (changes every sync)
  board-images  embedded artwork                          (changes only on an image refresh)

A cloud-side sync must never touch board-images — it has no access to the artwork source.
"""
import json, sys, pathlib, datetime, zoneinfo

BASE = pathlib.Path(__file__).parent
BLOCKS = {
    "config": '<script id="board-config" type="application/json">',
    "rows": '<script id="board-data" type="application/json">',
    "images": '<script id="board-images" type="application/json">',
}
CLOSE = "</script>"

argv = sys.argv[1:]


def flag(name):
    return name in argv


def opt(name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


args = [a for a in argv if not a.startswith("--")]
if opt("--config") in args:
    args.remove(opt("--config"))

CFG = json.loads((BASE / (opt("--config") or "config.json")).read_text(encoding="utf-8"))
props = CFG["notion"]["props"]

# ---- --sql : the SELECT the scheduled task should run -------------------------
if flag("--sql"):
    want = ["title", "stage", "ctype", "prio", "sched", "platform", "audience", "cat", "brand",
            "published", "approved", "render", "ratio", "imgtext", "cta", "caption", "prompt",
            "angle", "srcurl", "guard"]
    cols = []
    for k in want:
        name = props.get(k)
        if not name:
            continue
        col = f'"date:{name}:start"' if k in CFG["notion"].get("dateProps", []) else f'"{name}"'
        cols.append(f"{col} as {k}")
    cols.append("url")
    order = props.get(CFG["notion"].get("orderBy", "sched"))
    print("SELECT " + ", ".join(cols) +
          f' FROM "{CFG["notion"]["dataSource"]}"' +
          (f' ORDER BY "date:{order}:start"' if order else ""))
    sys.exit(0)

# ---- rows --------------------------------------------------------------------
rows = json.loads((BASE / "data.json").read_text(encoding="utf-8"))
if isinstance(rows, dict):
    rows = rows.get("results", [])

for r in rows:
    for k in CFG["notion"].get("listProps", []):
        v = r.get(k)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                v = [x for x in v.split(",") if x.strip()]
        r[k] = v if isinstance(v, list) else ([] if v in (None, "") else [v])
    for k in CFG["notion"].get("boolProps", []):
        v = r.get(k)
        r[k] = v is True or v == "__YES__" or v == 1


def block(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def swap(page, key, payload):
    opener = BLOCKS[key]
    i = page.index(opener) + len(opener)
    j = page.index(CLOSE, i)
    return page[:i] + payload + page[j:]


target = pathlib.Path(args[0]) if args else None
fresh = not (target and target.exists())
src = (BASE / "board_template.html") if fresh else target
page = src.read_text(encoding="utf-8")

if fresh:
    page = page.replace("__TITLE__", CFG["brand"]["title"])
    page = page.replace("__SUBTITLE__", CFG["brand"].get("subtitle", ""))

if fresh or flag("--config"):
    page = swap(page, "config", block(CFG))

tz = zoneinfo.ZoneInfo(CFG["locale"].get("timezone", "UTC"))
page = swap(page, "rows", block(
    {"synced": datetime.datetime.now(tz).isoformat(timespec="seconds"), "rows": rows}))

img_path = BASE / "images.json"
if fresh or flag("--images"):
    imgs = json.loads(img_path.read_text(encoding="utf-8")) if img_path.exists() else {}
    page = swap(page, "images", block(imgs))
    n_img = sum(len(v.get("files", [])) for v in imgs.values())
else:
    n_img = "kept"

out = target if target else (BASE / "board.html")
out.write_text(page, encoding="utf-8")
print(f"[{CFG['id']}] wrote {out.name} — {len(rows)} rows, "
      f"{sum(1 for r in rows if not r.get('published'))} active, images: {n_img}")
