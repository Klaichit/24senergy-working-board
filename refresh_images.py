#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incremental artwork refresh for the 24sEnergy board.

Encodes whatever PNG/JPG files are currently sitting in the staged uploads folder
and merges them into images.json, keeping every image that was already there.

  python3 refresh_images.py                     merge staged files into images.json
  python3 refresh_images.py --inventory inv.txt also prune entries missing from inv.txt
                                                (inv.txt = one "<folder>/<file>" per line,
                                                 the device's full current file list)

Writes manifest.json = {"cutoff": <epoch seconds>, "count": <files on device>}
so the next run only has to stage files newer than `cutoff`.
"""
import base64, io, json, pathlib, re, sys, time
from PIL import Image

BASE = pathlib.Path(__file__).parent
CFG_PATH = BASE / (sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else "config.json")
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))
IMGCFG = CFG.get("images", {})

SRC = pathlib.Path("/mnt/user-data/uploads") / IMGCFG.get("mountName", "images")
IMAGES = BASE / "images.json"
MANIFEST = BASE / "manifest.json"
DRIVE_MAP = BASE / "drive_folders.json"
WIDTH = IMGCFG.get("width", 760)
QUALITY = IMGCFG.get("quality", 80)
FOLDER_RE = re.compile(IMGCFG.get("folderPattern", r"^(\d{4}-\d{2}-\d{2})"))

inv_path = None
if "--inventory" in sys.argv:
    inv_path = pathlib.Path(sys.argv[sys.argv.index("--inventory") + 1])

drive = json.loads(DRIVE_MAP.read_text(encoding="utf-8")) if DRIVE_MAP.exists() else {}
data = json.loads(IMAGES.read_text(encoding="utf-8")) if IMAGES.exists() else {}


def key_of(folder_name):
    m = FOLDER_RE.match(folder_name)
    return m.group(1) if m else None


def encode(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.resize((WIDTH, round(h * WIDTH / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return {"name": path.stem, "w": w, "h": h,
            "src": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}


# ---- merge whatever is staged -------------------------------------------------
added = 0
if SRC.exists():
    for d in sorted(p for p in SRC.iterdir() if p.is_dir()):
        k = key_of(d.name)
        if not k:
            continue
        entry = data.setdefault(k, {"folder": d.name, "drive": drive.get(k), "files": []})
        entry["folder"] = d.name
        entry["drive"] = drive.get(k, entry.get("drive"))
        for f in sorted(list(d.glob("*.png")) + list(d.glob("*.jpg"))):
            rec = encode(f)
            entry["files"] = [x for x in entry["files"] if x["name"] != rec["name"]]
            entry["files"].append(rec)
            added += 1
        entry["files"].sort(key=lambda x: x["name"])

# ---- prune against the device's real inventory --------------------------------
removed = 0
count = None
if inv_path and inv_path.exists():
    lines = [l.strip() for l in inv_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    count = len(lines)
    keep = {}
    for line in lines:
        folder, _, fname = line.replace("\\", "/").rpartition("/")
        k = key_of(folder)
        if k:
            keep.setdefault(k, set()).add(pathlib.PurePath(fname).stem)
    for k in list(data):
        if k not in keep:
            removed += len(data[k]["files"]); del data[k]; continue
        before = len(data[k]["files"])
        data[k]["files"] = [f for f in data[k]["files"] if f["name"] in keep[k]]
        removed += before - len(data[k]["files"])
        if not data[k]["files"]:
            del data[k]

IMAGES.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

total = sum(len(v["files"]) for v in data.values())
MANIFEST.write_text(json.dumps(
    {"cutoff": int(time.time()), "count": count if count is not None else total,
     "folders": len(data), "images": total}, indent=2), encoding="utf-8")

missing = [v["folder"] for v in data.values() if not v.get("drive")]
print(f"images.json: {len(data)} folders, {total} images "
      f"(+{added} encoded, -{removed} pruned), {IMAGES.stat().st_size/1e6:.2f} MB")
if missing:
    print("NO DRIVE LINK for: " + " | ".join(missing) +
          "  -> add the folder id to drive_folders.json")
