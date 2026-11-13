"""Step 8 - YouTube metadata: title, description (with licence credits), tags, validation."""
from __future__ import annotations

from .config import Project

DEFAULT_DESCRIPTION = """{title}

{hours_text} of slow, cinematic ambience for sleep, study, reading and relaxation.
Let the scene drift in the background while you rest or focus.

{credits}
Visuals: AI-generated footage (Google Veo), edited and looped by {channel}.

#ambience #relaxing #sleep
"""


def hours_text(sec: float) -> tuple[str, str]:
    """('3', '3 hours'), ('2.5', '2.5 hours'), or minutes for sub-hour videos."""
    h = sec / 3600
    num = f"{h:g}" if abs(h - round(h)) < 1e-6 else f"{h:.1f}"
    if h < 1:
        m = round(sec / 60)
        return num, f"{m} minute" + ("" if m == 1 else "s")
    return num, (f"{num} hour" + ("" if num == "1" else "s"))


def credits(proj: Project) -> str:
    lines = []
    for l in proj.cfg["audio"]["layers"]:
        if l.get("attribution_required") or l.get("credit"):
            lines.append(f"- {l.get('credit') or l['file']}"
                         + (f" ({l['license']})" if l.get("license") else "")
                         + (f" {l['source']}" if l.get("source") and l.get("attribution_required") else ""))
    return ("Audio credits:\n" + "\n".join(lines) + "\n") if lines else ""


def validate(md: dict) -> list[str]:
    errs = []
    if len(md["title"]) > 100:
        errs.append(f"title is {len(md['title'])} chars (max 100)")
    if not md["title"].strip():
        errs.append("title is empty")
    if len(md["description"].encode("utf-8")) > 5000:
        errs.append(f"description is {len(md['description'].encode('utf-8'))} bytes (max 5000)")
    for f in ("title", "description"):
        if "<" in md[f] or ">" in md[f]:
            errs.append(f"{f} contains '<' or '>' (rejected by YouTube)")
    tag_len = sum(len(t) + (2 if " " in t else 0) for t in md["tags"]) + max(0, len(md["tags"]) - 1)
    if tag_len > 500:
        errs.append(f"tags total {tag_len} chars (max 500)")
    if md["privacy"] not in ("private", "unlisted", "public"):
        errs.append("privacy must be private | unlisted | public")
    return errs


def run(proj: Project) -> dict:
    y = proj.cfg["youtube"]
    title = proj.cfg["project"]["title"]
    num, htxt = hours_text(proj.duration)
    ctx = {"title": title, "hours": num, "hours_text": htxt[0].upper() + htxt[1:],
           "length": htxt.title(),
           "channel": proj.cfg["project"].get("channel", "Driftscape"), "credits": credits(proj)}
    md = {
        "title": y["title"].format(**ctx).strip(),
        "description": (y.get("description") or DEFAULT_DESCRIPTION).format(**ctx).strip() + "\n",
        "tags": [t.strip() for t in y.get("tags", []) if t.strip()],
        "category_id": str(y["category_id"]),
        "privacy": y["privacy"],
        "made_for_kids": bool(y["made_for_kids"]),
        "contains_synthetic_media": bool(y["contains_synthetic_media"]),
        "default_language": y.get("default_language", "en"),
    }
    errs = validate(md)
    md["validation_errors"] = errs
    proj.save_json("out/metadata.json", md)
    proj.p("out", "description.txt").write_text(md["description"])
    print(f"  title: {md['title']}")
    print(f"  metadata -> {proj.out / 'metadata.json'} (privacy: {md['privacy']}, "
          f"AI disclosure: {md['contains_synthetic_media']})")
    for e in errs:
        print(f"  ! {e}")
    return md
