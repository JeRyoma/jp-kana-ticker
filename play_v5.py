#!/usr/bin/env python3
"""V5 Taskbar Ticker: 100 unique illustrated words + 55 non-template expressions each weekday."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time
import json
from pathlib import Path
from random import Random
from zoneinfo import ZoneInfo

from learning_data import WORDS, THEMES
from expanded_vocab_v5 import EXPANSION
from scenes_v5 import SCENES, COMMON
from generate import base_url, learning_day, rss_xml, html_page

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "docs"
SETTINGS = ROOT / "config.json"

if len(THEMES) != 20 or len(EXPANSION) != 20 or len(SCENES) != 20:
    raise ValueError("There should be 20 paired learning themes")

# Preserve all previously learned words; make sure new ones do not overwrite old ones.
VOCABULARY = dict(WORDS)
GROUPS = []
for ix, (_, kata, hira, _) in enumerate(THEMES):
    group = list(dict.fromkeys(kata.split() + hira.split() + list(EXPANSION[ix])))
    for spelling, data in EXPANSION[ix].items():
        if spelling in VOCABULARY:
            raise ValueError(f"Unexpected duplicate spelling: {spelling}")
        VOCABULARY[spelling] = data
    GROUPS.append(group)

if len(VOCABULARY) < 500:
    raise ValueError(f"Vocabulary pool is unexpectedly small: {len(VOCABULARY)}")

def unique_extend(target: list[str], source, limit: int | None = None):
    """Append only distinct words, optionally limiting this source's contribution."""
    seen = set(target)
    added = 0
    for spelling in source:
        if spelling not in seen:
            target.append(spelling)
            seen.add(spelling)
            added += 1
            if limit is not None and added >= limit:
                break

def balanced_words(day: int, target: int = 100) -> list[str]:
    """Daily focus + old/new topic echoes + shuffled large pool (never artificial clones)."""
    ix = (day - 1) % len(GROUPS)
    rng = Random(day * 10007 + 17)
    selected = []
    focus = GROUPS[ix][:]
    rng.shuffle(focus)
    unique_extend(selected, focus)
    for delta, limit in ((-1, 12), (1, 12), (-5, 8)):
        extra = GROUPS[(ix + delta) % len(GROUPS)][:]
        rng.shuffle(extra)
        unique_extend(selected, extra, limit=limit)
    # Pull from the full 550+ vocabulary bank, not only 10 familiar topic words.
    remainder = list(VOCABULARY)
    rng.shuffle(remainder)
    unique_extend(selected, remainder, limit=max(0, target - len(selected)))
    selected = selected[:target]
    rng.shuffle(selected)

    # Mix kana rather than showing 40 consecutive loanwords then 40 hiragana words.
    hira = [w for w in selected if VOCABULARY[w]["script"] == "hiragana"]
    kata = [w for w in selected if VOCABULARY[w]["script"] != "hiragana"]
    if min(len(hira), len(kata)) < 30:
        raise ValueError("Poor hiragana/katakana balance")
    return selected

def varied_scenes(day: int, target: int = 55) -> list[dict]:
    ix = (day - 1) % len(SCENES)
    rng = Random(day * 10009 + 19)
    # Four different contexts and practical conversational connectors.
    groups = [ix, (ix-1)%20, (ix+1)%20, (ix+5+day//20)%20, (ix+10)%20]
    chosen = []
    seen = set()
    for group_index in groups:
        scenes = SCENES[group_index][:]
        rng.shuffle(scenes)
        for row in scenes:
            if row["value"] not in seen:
                chosen.append(row)
                seen.add(row["value"])
    common = COMMON[:]
    rng.shuffle(common)
    for row in common:
        if row["value"] not in seen:
            chosen.append(row)
            seen.add(row["value"])
    # Mix whole situational dialogues without mass-generating grammatical templates.
    rng.shuffle(chosen)
    return chosen[:target]

def daily_content(day: int, settings: dict | None = None) -> dict:
    settings = settings or json.loads(SETTINGS.read_text(encoding="utf-8"))
    target_words = int(settings.get("daily_unique_words", 100))
    target_scenes = int(settings.get("daily_varied_sentences", 55))
    if not 50 <= target_words <= len(VOCABULARY):
        raise ValueError("daily_unique_words must be between 50 and total vocabulary size")
    if not 20 <= target_scenes <= 65:
        raise ValueError("daily_varied_sentences must be between 20 and 65")

    words = balanced_words(day, target_words)
    scene_rows = varied_scenes(day, target_scenes)
    word_items = []
    for word in words:
        data = VOCABULARY[word]
        word_items.append({
            "value": word, "reading": data["reading"], "meaning": data["meaning"],
            "emoji": data["emoji"], "kind": "word", "script": data["script"],
            "title": f'{data["emoji"]} {word} ({data["reading"]}) · {data["meaning"]}',
        })
    scene_items = [{
        "value": row["value"], "reading": row["reading"], "meaning": row["meaning"],
        "emoji": row["emoji"], "kind": "sentence", "script": "mixed",
        "title": f'{row["emoji"]} {row["value"]} ({row["reading"]}) · {row["meaning"]}',
    } for row in scene_rows]
    # Even the first 50 RSS entries should contain many kinds of words and scenarios.
    rng = Random(day * 10037 + 29)
    rng.shuffle(word_items)
    rng.shuffle(scene_items)
    items = []
    while word_items or scene_items:
        for _ in range(2):
            if word_items: items.append(word_items.pop())
        if scene_items: items.append(scene_items.pop())
    if len({it["value"] for it in items}) != len(items):
        raise ValueError("Duplicate display item")
    ix = (day - 1) % len(THEMES)
    title = f'{day}일차 · {THEMES[ix][0]} + 다양한 생활 표현'
    return {
        "day": day, "theme": THEMES[ix][0],
        "companion_theme": THEMES[(ix-1)%20][0], "title": title,
        "items": items,
        "word_count": len(words), "sentence_count": len(scene_rows),
    }

def generate(on_date: date, settings: dict | None = None) -> dict:
    settings = settings or json.loads(SETTINGS.read_text(encoding="utf-8"))
    day = learning_day(on_date, date.fromisoformat(settings["start_date"]))
    now = datetime.combine(on_date, time(7,17), tzinfo=ZoneInfo(settings.get("timezone", "Asia/Seoul")))
    lesson = daily_content(day, settings)
    site = base_url()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = lambda binary: binary.replace(b"jpplay:v4:", b"jpplay:v5:")
    (OUTPUT/"rss.xml").write_bytes(suffix(rss_xml(now, lesson, site)))
    (OUTPUT/"rss-words.xml").write_bytes(suffix(rss_xml(now, lesson, site, ("word","review_word"))))
    (OUTPUT/"rss-sentences.xml").write_bytes(suffix(rss_xml(now, lesson, site, ("sentence","review_sentence","dialogue"))))
    page = html_page(now, lesson, on_date.weekday() > 4)
    page = page.replace("그림 단어에서 생활 문장까지", "다양한 단어와 실생활 표현")
    page = page.replace("낱글자 암기 없이, 쉬운 단어 → 짧은 문장 → 질문과 대답으로 이어지는 초급 일본어입니다.", "하루 100개 서로 다른 일본어 단어와 주제별 생활 표현을 만나는 초급 일본어입니다.")
    (OUTPUT/"index.html").write_text(page, encoding="utf-8")
    (OUTPUT/".nojekyll").touch()
    return lesson

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="Date for reproducible preview (YYYY-MM-DD)")
    opt = p.parse_args()
    today = date.fromisoformat(opt.date) if opt.date else datetime.now(ZoneInfo("Asia/Seoul")).date()
    lesson = generate(today)
    print(f'Japanese ticker v5, {today}: day {lesson["day"]}, '
          f'{lesson["word_count"]} distinct words + {lesson["sentence_count"]} varied expressions')

if __name__ == "__main__":
    main()
