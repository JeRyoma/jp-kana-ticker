import sys
import unittest
from pathlib import Path
from datetime import date
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate import learning_day, rss_xml
from play_v5 import VOCABULARY, GROUPS, daily_content, balanced_words, varied_scenes
from scenes_v5 import SCENES, COMMON
from expanded_vocab_v5 import EXPANSION

class RichCurriculumTests(unittest.TestCase):
    def test_starts_friday_weekend_stays_same(self):
        start=date(2026,10,23)
        for d,num in [(date(2026,10,23),1),(date(2026,10,24),1),
                      (date(2026,10,25),1),(date(2026,10,26),2),
                      (date(2026,10,27),3)]:
            self.assertEqual(learning_day(d,start),num)
    def test_expanded_pool_and_both_scripts(self):
        self.assertEqual(len(GROUPS),20)
        self.assertEqual(len(SCENES),20)
        self.assertGreaterEqual(len(VOCABULARY),550)
        self.assertGreaterEqual(sum(len(x) for x in EXPANSION),350)
        self.assertEqual(len(COMMON),20)
        for idx,group in enumerate(GROUPS):
            self.assertGreaterEqual(len(set(group)),24)
            for word in group:
                self.assertIn(word,VOCABULARY)
        for scene in SCENES:
            self.assertEqual(len(scene),10)
    def test_every_day_has_many_distinct_words_and_non_template_sentences(self):
        for day in range(1,221):
            with self.subTest(day=day):
                lesson = daily_content(day)
                self.assertEqual(lesson["word_count"],100)
                self.assertEqual(lesson["sentence_count"],55)
                self.assertEqual(len(lesson["items"]),155)
                self.assertEqual(len({x["value"] for x in lesson["items"]}),155)
                self.assertEqual(lesson,daily_content(day))
                words=[x for x in lesson["items"] if x["kind"]=="word"]
                sentences=[x for x in lesson["items"] if x["kind"]=="sentence"]
                self.assertGreaterEqual(sum(x["script"]=="hiragana" for x in words),30)
                self.assertGreaterEqual(sum(x["script"]=="katakana" for x in words),30)
                self.assertGreaterEqual(len(sentences),50)
                # Early feed entries must not be crowded with duplicated sentence forms.
                self.assertGreaterEqual(sum(x["kind"]=="word" for x in lesson["items"][:50]),30)
                self.assertGreaterEqual(sum(x["kind"]=="sentence" for x in lesson["items"][:50]),15)
                for item in lesson["items"]:
                    self.assertIn(item["reading"],item["title"])
                    self.assertIn(item["meaning"],item["title"])
                    self.assertNotIn("읽어볼까요",item["title"])
    def test_rss_items_xml_and_filtering(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        lesson=daily_content(1)
        now=datetime(2026,10,23,7,17,tzinfo=ZoneInfo("Asia/Seoul"))
        data=rss_xml(now,lesson,"https://jeryoma.github.io/jp-kana-ticker")
        root=ET.fromstring(data)
        self.assertEqual(len(root.findall("./channel/item")),155)
        self.assertEqual(len(ET.fromstring(rss_xml(now,lesson,"https://jeryoma.github.io/jp-kana-ticker",("word","review_word"))).findall("./channel/item")),100)

if __name__ == "__main__":
    unittest.main()
