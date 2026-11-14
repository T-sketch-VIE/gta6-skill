#!/usr/bin/env python3
"""Prueft das Plugin: elf Skills, Frontmatter, Sicherheitsregel, keine Gedankenstriche."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [
    "kampagnen-finder", "stream-finder", "momente-finder", "clip-schneider", "untertitel",
    "hook-schreiber", "caption-und-hashtags", "regel-check", "trend-radar",
    "post-plan", "auszahlungs-tracker",
]
# Skills, die etwas verschicken koennten: Regel "Ja" muss drinstehen.
MIT_JA_REGEL = SKILLS
KEIN_ERFINDEN = SKILLS
GEDANKENSTRICHE = ("–", "—", " -- ")  # Halbgeviert, Geviert, Doppelstrich mit Leerzeichen (CLI-Flags wie --out sind erlaubt)

fehler = []


def f(msg):
    fehler.append(msg)


for name in SKILLS:
    p = ROOT / "skills" / name / "SKILL.md"
    if not p.exists():
        f(f"fehlt: {p.relative_to(ROOT)}")
        continue
    t = p.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m:
        f(f"{name}: kein Frontmatter")
        continue
    kopf = m.group(1)
    if not re.search(rf"^name: {re.escape(name)}$", kopf, re.M):
        f(f"{name}: name im Frontmatter stimmt nicht")
    if "description:" not in kopf:
        f(f"{name}: description fehlt")
    if name in MIT_JA_REGEL and "Ja" not in t:
        f(f"{name}: Ja-Regel fehlt")
    if name in KEIN_ERFINDEN and "erfind" not in t.lower():
        f(f"{name}: Nichts-erfinden-Regel fehlt")

extra = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")} - set(SKILLS)
if extra:
    f(f"unerwartete Skills: {sorted(extra)}")

for datei in ["plugin.json", "marketplace.json"]:
    try:
        json.loads((ROOT / ".claude-plugin" / datei).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        f(f"{datei}: {e}")

for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or p.suffix not in {".md", ".json", ".py"}:
        continue
    if p.name == "pruefen.py":
        continue
    text = p.read_text(encoding="utf-8")
    # Frontmatter-Trenner und Tabellen-Trennzeilen sind keine Gedankenstriche
    text = re.sub(r"(?m)^[\s|:-]*-{3,}[\s|:-]*$", "", text)
    for zeichen in GEDANKENSTRICHE:
        if zeichen in text:
            f(f"{p.relative_to(ROOT)}: enthaelt {zeichen!r}")

if (ROOT / "LICENSE").read_text(encoding="utf-8").split("\n")[0] != "MIT License":
    f("LICENSE ist nicht MIT")

if fehler:
    print("FEHLER:")
    for x in fehler:
        print(" -", x)
    sys.exit(1)
print(f"ok: {len(SKILLS)} Skills, Frontmatter, Regeln, JSON, keine Gedankenstriche")
