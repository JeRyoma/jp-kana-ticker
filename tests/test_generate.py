import sys
import unittest
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate import (
    first_workday, learning_day, daily_content, rss_xml, html_page,
    theme_words, day_index, all_sentence_options, dialogues
)
from learning_data import THEMES, WORDS


class WordSentenceTickerTests(unittest.TestCase):
    def test_weekday_progression_and_weekend_freeze(self):
        start=date(2026,10,22)
        dates={'2026-10-22':1,'2026-10-23':2,'2026-10-24':2,
               '2026-10-25':2,'2026-10-26':3,'2026-10-30':7,
               '2026-10-31':7,'2026-11-02':8,'2026-11-12':16,
               '2026-11-13':17,'2026-11-18':20,'2026-11-19':21}
        for ds,expected in dates.items():
            with self.subTest(date=ds):self.assertEqual(learning_day(date.fromisoformat(ds),start),expected)
        self.assertEqual(first_workday(date(2026,10,24)),date(2026,10,26))
        for x in range(1,950):
            current=start+timedelta(days=x)
            idx=learning_day(current,start)
            if current.weekday()>=5:
                self.assertEqual(idx,learning_day(current-timedelta(days=current.weekday()-4),start))
            else:
                self.assertEqual(idx,learning_day(current-timedelta(days=1),start)+1 if current.weekday()!=0 else learning_day(current-timedelta(days=3),start)+1)

    def test_full_bank_and_kana_mix(self):
        self.assertEqual(len(THEMES),20)
        for i,(_,k,h,n) in enumerate(THEMES):
            self.assertEqual(i,n)
            self.assertEqual(len(k.split()),5)
            self.assertEqual(len(h.split()),5)
            for word in (k+' '+h).split():self.assertIn(word,WORDS)
        self.assertNotEqual(theme_words(0,0),theme_words(0,1))
        self.assertEqual(len(set(theme_words(0))),10)
        self.assertEqual(day_index(21),0)

    def test_fully_formatted_items_no_letter_drills(self):
        for d in range(1,301):
            lesson=daily_content(d)
            self.assertGreaterEqual(len(lesson['items']),80)
            self.assertGreaterEqual(lesson['word_count'],30)
            self.assertGreaterEqual(lesson['sentence_count'],50)
            self.assertEqual(lesson,daily_content(d))
            items=lesson['items']
            self.assertEqual(len(set(it['value'] for it in items)),len(items))
            self.assertTrue(any(it['script']=='hiragana' for it in items))
            self.assertTrue(any(it['script']=='katakana' for it in items))
            self.assertTrue(any(it['kind']=='dialogue' for it in items))
            for it in items:
                self.assertNotIn('읽어볼까요',it['title'])
                self.assertNotIn('무슨 소리',it['title'])
                self.assertTrue(it['reading'] and it['meaning'])
                self.assertIn(it['reading'],it['title'])
                self.assertIn(it['meaning'],it['title'])
                self.assertGreaterEqual(len(it['value']),2)
        first=daily_content(1)
        jp={x['value'] for x in first['items']}
        for sentence in ('バナナをたべたいです','これはバナナです','バナナがすきです',
                         'バナナをたべたい？','うん、たべたい！','うん、バナナだよ'):
            self.assertIn(sentence,jp)
        self.assertEqual(first['day'],1)
        self.assertEqual(first['word_count'],36)

    def test_does_not_use_wrong_verb_for_known_items(self):
        self.assertNotIn('ジュースをたべたいです',{x['value'] for x in all_sentence_options('ジュース',2)})
        self.assertIn('ジュースをのみたいです',{x['value'] for x in all_sentence_options('ジュース',2)})
        self.assertNotIn('かぜがみえます',{x['value'] for x in all_sentence_options('かぜ',19)})
        self.assertNotIn('ダンスがほしいです',{x['value'] for x in all_sentence_options('ダンス',8)})
        self.assertIn('ズボンをはきます',{x['value'] for x in all_sentence_options('ズボン',9)})
        self.assertIn('マスクをします',{x['value'] for x in all_sentence_options('マスク',9)})
        self.assertIn('おはようございます',{x['value'] for x in all_sentence_options('おはよう',13)})

    def test_rss_feeds_and_companion_page(self):
        now=datetime(2026,10,22,7,17,tzinfo=ZoneInfo('Asia/Seoul'))
        for d in [1,2,9,14,19,20,21,101,300]:
            l=daily_content(d)
            for kinds,expected in [
                (None,len(l['items'])),
                (('word','review_word'),l['word_count']),
                (('sentence','review_sentence','dialogue'),l['sentence_count'])]:
                x=ET.fromstring(rss_xml(now,l,'https://example.com/jp-kana-ticker',kinds))
                nodes=x.findall('./channel/item')
                self.assertEqual(len(nodes),expected)
                self.assertEqual(len({n.find('guid').text for n in nodes}),expected)
                self.assertTrue(all(n.find('title').text and n.find('description').text for n in nodes))
                self.assertTrue(all(n.find('link').text.startswith('https://example.com/jp-kana-ticker/#item-') for n in nodes))
            html=html_page(now,l,False)
            self.assertIn('rss-words.xml',html)
            self.assertIn('rss-sentences.xml',html)
            self.assertIn('🔊 일본어 듣기',html)
            self.assertNotIn('낱글자 암기',html.split('<section class="grid">')[1])

if __name__=='__main__':unittest.main()
