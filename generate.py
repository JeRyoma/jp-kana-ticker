#!/usr/bin/env python3
"""Every-workday beginner Japanese vocabulary + sentence RSS.

No isolated letters, tests, hidden pronunciation, or instructional questions.
The exact same lesson is served on weekends. Fully offline; Python 3.11+.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from email.utils import format_datetime
from html import escape
import json
import os
from pathlib import Path
import random
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from learning_data import WORDS, THEMES, PHRASES

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'docs'
CONF = ROOT / 'config.json'


def first_workday(day: date) -> date:
    return day if day.weekday() < 5 else day + timedelta(days=7-day.weekday())


def learning_day(today: date, start: date) -> int:
    beginning = first_workday(start)
    if today <= beginning:
        return 1
    days = (today - beginning).days + 1
    weeks, remainder = divmod(days, 7)
    return 5*weeks + sum((beginning + timedelta(days=7*weeks+i)).weekday() < 5
                         for i in range(remainder))


def day_index(day: int) -> int:
    return (day - 1) % len(THEMES)


def theme_words(idx: int, cycle=0) -> list[str]:
    _, k, h, _ = THEMES[idx]
    # Order changes when topics repeat, all original natural Japanese spellings stay unchanged.
    a, b = k.split(), h.split()
    offset = cycle % 5
    a, b = a[offset:] + a[:offset], b[offset:] + b[:offset]
    return [v for pair in zip(a,b) for v in pair]


def object_particle(meaning: str) -> str:
    # Used only in Korean meanings, not Japanese grammar.
    tail = meaning.rstrip(')')[-1]
    return '을' if '가' <= tail <= '힣' and (ord(tail)-0xAC00)%28 else '를'


def subject_particle(meaning: str) -> str:
    tail = meaning.rstrip(')')[-1]
    return '이' if '가' <= tail <= '힣' and (ord(tail)-0xAC00)%28 else '가'


def entry(jp: str, reading: str, meaning: str, emoji='💬', kind='sentence', script='mixed') -> dict:
    return {'value':jp,'reading':reading,'meaning':meaning,'emoji':emoji,'kind':kind,'script':script,
            'title':f'{emoji} {jp} ({reading}) · {meaning}'}


def word_entry(word: str, kind='word') -> dict:
    d = WORDS[word]
    flag = '🔁 ' if kind=='review_word' else ''
    out = entry(d['value'],d['reading'],d['meaning'],flag+d['emoji'],kind,d['script'])
    out['title'] = f"{flag}{d['emoji']} {word} ({d['reading']}) · {d['meaning']}"
    return out


def common(word: str, mode: str) -> dict:
    w = WORDS[word]; jp=word; rd=w['reading']; mn=w['meaning']; em=w['emoji']
    p = {
      'this': (f'これは{jp}です',f'코레와 {rd}데스',f'이것은 {mn}예요'),
      'is_it':(f'これは{jp}ですか？',f'코레와 {rd}데스카?',f'이것은 {mn}인가요?'),
      'like':(f'{jp}がすきです',f'{rd}가 스키데스',f'{mn}{object_particle(mn)} 좋아해요'),
      'where':(f'{jp}はどこですか？',f'{rd}와 도코데스카?',f'{mn}{subject_particle(mn)} 어디에 있나요?'),
      'have':(f'{jp}があります',f'{rd}가 아리마스',f'{mn}{subject_particle(mn)} 있어요'),
      'animate':(f'{jp}がいます',f'{rd}가 이마스',f'{mn}{subject_particle(mn)} 있어요'),
      'want':(f'{jp}がほしいです',f'{rd}가 호시이데스',f'{mn}{object_particle(mn)} 갖고 싶어요'),
      'eat':(f'{jp}をたべたいです',f'{rd}오 타베타이데스',f'{mn}{object_particle(mn)} 먹고 싶어요'),
      'drink':(f'{jp}をのみたいです',f'{rd}오 노미타이데스',f'{mn}{object_particle(mn)} 마시고 싶어요'),
      'give':(f'{jp}をください',f'{rd}오 쿠다사이',f'{mn} 주세요'),
      'see':(f'{jp}をみたいです',f'{rd}오 미타이데스',f'{mn}{object_particle(mn)} 보고 싶어요'),
      'ride':(f'{jp}にのりたいです',f'{rd}니 노리타이데스',f'{mn}에 타고 싶어요'),
      'use':(f'{jp}をつかいます',f'{rd}오 츠카이마스',f'{mn}{object_particle(mn)} 사용해요'),
      'go':(f'{jp}にいきます',f'{rd}니 이키마스',f'{mn}에 가요'),
      'play':(f'{jp}であそびます',f'{rd}데 아소비마스',f'{mn}(으)로 놀아요'),
      'look':(f'{jp}がみえます',f'{rd}가 미에마스',f'{mn}{subject_particle(mn)} 보여요'),
      'pretty':(f'{jp}はきれいです',f'{rd}와 키레이데스',f'{mn}{subject_particle(mn)} 예뻐요'),
      'colorpen':(f'{jp}のペンです',f'{rd}노 펜데스',f'{mn} 펜이에요'),
      'colorlike':(f'{jp}のペンがすきです',f'{rd}노 펜가 스키데스',f'{mn} 펜을 좋아해요'),
      'simpleeat':(f'{jp}をたべます',f'{rd}오 타베마스',f'{mn}{object_particle(mn)} 먹어요'),
    }
    return entry(*p[mode], emoji=em)


# Inflections and context-sensitive phrases. These are individually curated; not
# all nouns accept the same verb (e.g. ride a bus, drink juice, wear shoes).
SPECIAL: dict[str, list[tuple[str,str,str]]] = {
 'ハイキング':[('ハイキングにいきます','하이킹구니 이키마스','하이킹하러 가요'),('ハイキングがすきです','하이킹구가 스키데스','하이킹을 좋아해요')],
 'レインコート':[('レインコートをきます','레잉코-토오 키마스','비옷을 입어요')],
 'スニーカー':[('スニーカーをはきます','스니-카-오 하키마스','운동화를 신어요')],
 'サンダル':[('サンダルをはきます','산다루오 하키마스','샌들을 신어요')],
 'テント':[('テントをたてます','텐토오 타테마스','텐트를 쳐요')],
 'ゲーム':[('ゲームをします','게-무오 시마스','게임을 해요')],
 'アニメ':[('アニメをみます','아니메오 미마스','애니메이션을 봐요')],
 'ダンス':[('ダンスをします','단스오 시마스','춤을 춰요')],
 'ピアノ':[('ピアノをひきます','피아노오 히키마스','피아노를 쳐요')],
 'ギター':[('ギターをひきます','기타-오 히키마스','기타를 쳐요')],
 'あそぶ':[('あそびます','아소비마스','놀아요'),('いっしょにあそびます','잇쇼니 아소비마스','함께 놀아요'),('あそびたいです','아소비타이데스','놀고 싶어요')],
 'うたう':[('うたいます','우타이마스','노래해요'),('いっしょにうたいます','잇쇼니 우타이마스','함께 노래해요'),('うたいたいです','우타이타이데스','노래하고 싶어요')],
 'おどる':[('おどります','오도리마스','춤춰요'),('いっしょにおどります','잇쇼니 오도리마스','함께 춤춰요'),('おどりたいです','오도리타이데스','춤추고 싶어요')],
 'みる':[('みます','미마스','봐요'),('テレビをみます','테레비오 미마스','TV를 봐요'),('みたいです','미타이데스','보고 싶어요')],
 'きく':[('ききます','키키마스','들어요'),('おんがくをききます','옹가쿠오 키키마스','음악을 들어요'),('ききたいです','키키타이데스','듣고 싶어요')],
 'マスク':[('マスクをします','마스쿠오 시마스','마스크를 써요')],
 'メガネ':[('メガネをかけます','메가네오 카케마스','안경을 써요')],
 'シャツ':[('シャツをきます','샤츠오 키마스','셔츠를 입어요')],
 'ズボン':[('ズボンをはきます','즈봉오 하키마스','바지를 입어요')],
 'ソックス':[('ソックスをはきます','솟쿠스오 하키마스','양말을 신어요')],
 'てのひら':[('てのひらをみせます','테노히라오 미세마스','손바닥을 보여줘요'),('てのひらをあらいます','테노히라오 아라이마스','손바닥을 씻어요')],
 'ひとみ':[('ひとみがきれいです','히토미가 키레이데스','눈동자가 예뻐요')],
 'えほん':[('えほんをよみます','에홍오 요미마스','그림책을 읽어요')],
 'きのえだ':[('きのえだがあります','키노에다가 아리마스','나뭇가지가 있어요')],
 'て':[('てをあらいます','테오 아라이마스','손을 씻어요'),('てをあげます','테오 아게마스','손을 들어요')],
 'あし':[('あしをあらいます','아시오 아라이마스','발을 씻어요'),('あしがいたいです','아시가 이타이데스','발이 아파요')],
 'かお':[('かおをあらいます','카오오 아라이마스','얼굴을 씻어요'),('かおをみます','카오오 미마스','얼굴을 봐요')],
 'め':[('めをとじます','메오 토지마스','눈을 감아요'),('めをあけます','메오 아케마스','눈을 떠요')],
 'みみ':[('みみでききます','미미데 키키마스','귀로 들어요'),('みみがいたいです','미미가 이타이데스','귀가 아파요')],
 'え':[('えをかきます','에오 카키마스','그림을 그려요')],
 'いろ':[('いろをえらびます','이로오 에라비마스','색을 골라요')],
 'かたち':[('かたちをみます','카타치오 미마스','모양을 봐요')],
 'あじ':[('あじはどうですか？','아지와 도-데스카?','맛은 어때요?'),('いいあじです','이이 아지데스','좋은 맛이에요')],
 'おいしい':[('おいしいです','오이시-데스','맛있어요'),('とてもおいしいです','토테모 오이시-데스','정말 맛있어요'),('おいしいですか？','오이시-데스카?','맛있나요?')],
 'おなか':[('おなかがすきました','오나카가 스키마시타','배가 고파졌어요'),('おなかがいっぱいです','오나카가 잇파이데스','배가 불러요')],
 'バイバイ':[('バイバイ、またね','바이바이, 마타네','잘 가, 또 봐'),('バイバイ！','바이바이!','잘 가!')],
 'ハロー':[('ハロー！','하로-!','안녕!(영어식 인사)'),('ハロー、みんな！','하로-, 민나!','안녕, 모두들!')],
 'サンキュー':[('サンキュー！','상큐-!','고마워!(영어식)'),('サンキュー、ママ！','상큐-, 마마!','고마워, 엄마!')],
 'グッバイ':[('グッバイ！','굿바이!','잘 가!(영어식)'),('グッバイ、またね','굿바이, 마타네','잘 가, 또 봐')],
 'スマイル':[('スマイル！','스마이루!','웃어요!'),('スマイルがすきです','스마이루가 스키데스','미소를 좋아해요')],
 'おはよう':[('おはよう！','오하요-!','좋은 아침!'),('おはよう、ママ','오하요-, 마마','좋은 아침, 엄마'),('おはようございます','오하요-고자이마스','안녕하세요(아침 인사)')],
 'こんにちは':[('こんにちは！','콘니치와!','안녕하세요!'),('せんせい、こんにちは','센세-, 콘니치와','선생님, 안녕하세요')],
 'ありがとう':[('ありがとう！','아리가토-!','고마워!'),('どうもありがとう','도-모 아리가토-','정말 고마워')],
 'おやすみ':[('おやすみ！','오야스미!','잘 자!'),('おやすみ、ママ','오야스미, 마마','잘 자, 엄마')],
 'またね':[('またね！','마타네!','또 봐!'),('バイバイ、またね','바이바이, 마타네','잘 가, 또 봐')],
 'なまえ':[('なまえはなんですか？','나마에와 난데스카?','이름이 뭐예요?'),('わたしのなまえ','와타시노 나마에','내 이름')],
 'エレベーター':[('エレベーターにのります','에레베-타-니 노리마스','엘리베이터를 타요')],
 'そと':[('そとにでます','소토니 데마스','밖으로 나가요'),('そとであそびます','소토데 아소비마스','밖에서 놀아요')],
 'みち':[('このみちはながいです','코노 미치와 나가이데스','이 길은 길어요'),('みちをあるきます','미치오 아루키마스','길을 걸어요')],
 'えき':[('えきにいきます','에키니 이키마스','역에 가요')],
 'はしる':[('はしります','하시리마스','달려요'),('はしりたいです','하시리타이데스','달리고 싶어요'),('いっしょにはしります','잇쇼니 하시리마스','함께 달려요')],
 'あるく':[('あるきます','아루키마스','걸어요'),('あるきたいです','아루키타이데스','걷고 싶어요'),('いっしょにあるきます','잇쇼니 아루키마스','함께 걸어요')],
 'とぶ':[('とびます','토비마스','뛰거나 날아요'),('とびたいです','토비타이데스','뛰거나 날고 싶어요')],
 'およぐ':[('およぎます','오요기마스','수영해요'),('およぎたいです','오요기타이데스','수영하고 싶어요')],
 'たつ':[('たちます','타치마스','일어서요'),('ここにたちます','코코니 타치마스','여기에 서요')],
 'サッカー':[('サッカーをします','삿카-오 시마스','축구해요')],
 'テニス':[('テニスをします','테니스오 시마스','테니스 쳐요')],
 'バスケ':[('バスケをします','바스케오 시마스','농구해요')],
 'ボール':[('ボールをなげます','보-루오 나게마스','공을 던져요')],
 'ゴール':[('ゴールをめざします','고-루오 메자시마스','골을 노려요')],
 'うれしい':[('うれしいです','우레시-데스','기뻐요'),('とてもうれしいです','토테모 우레시-데스','정말 기뻐요')],
 'たのしい':[('たのしいです','타노시-데스','즐거워요'),('とてもたのしいです','토테모 타노시-데스','정말 즐거워요')],
 'かなしい':[('かなしいです','카나시-데스','슬퍼요'),('ちょっとかなしいです','촛토 카나시-데스','조금 슬퍼요')],
 'ねむい':[('ねむいです','네무이데스','졸려요'),('ちょっとねむいです','촛토 네무이데스','조금 졸려요')],
 'げんき':[('げんきです','겡키데스','잘 지내요'),('げんきですか？','겡키데스카?','잘 지내나요?')],
 'ハッピー':[('ハッピーです','핫피-데스','행복해요'),('きょうはハッピーです','쿄-와 핫피-데스','오늘은 행복해요')],
 'ラッキー':[('ラッキーです','랏키-데스','운이 좋아요'),('きょうはラッキーです','쿄-와 랏키-데스','오늘은 운이 좋아요')],
 'グッド':[('グッドです','굿도데스','좋아요'),('グッド！','굿도!','좋아!')],
 'オッケー':[('オッケーです','옷케-데스','괜찮아요'),('オッケー、いこう','옷케-, 이코-','좋아, 가자')],
 'さとう':[('さとうをいれます','사토-오 이레마스','설탕을 넣어요')],
 'ココア':[('ココアをのみます','코코아오 노미마스','코코아를 마셔요')],
 'ソース':[('ソースをかけます','소-스오 카케마스','소스를 뿌려요')],
 'しお':[('しおをいれます','시오오 이레마스','소금을 넣어요')],
 'つき':[('つきがみえます','츠키가 미에마스','달이 보여요')],
 'かぜ':[('かぜがふきます','카제가 후키마스','바람이 불어요')],
 'なつ':[('いまはなつです','이마와 나츠데스','지금은 여름이에요'),('なつがすきです','나츠가 스키데스','여름을 좋아해요')],
}

VERBAL = {'あそぶ','うたう','おどる','みる','きく','はしる','あるく','とぶ','およぐ','たつ'}
FEELINGS = {'うれしい','たのしい','かなしい','ねむい','げんき','ハッピー','ラッキー','グッド','オッケー','スマイル'}
GREETINGS = {'ハロー','バイバイ','サンキュー','グッバイ','おはよう','こんにちは','ありがとう','おやすみ','またね'}
PERSON_SPECIAL = VERBAL | FEELINGS | GREETINGS | {'おいしい','おなか','あじ','なまえ'}
DRINKS = {'ジュース','みず','おちゃ','ココア','スープ'}
VEHICLES = {'バス','タクシー','バイク','トラック','ボート','くるま','でんしゃ','ふね'}
PLANTS = {'はな','くさ','き','もり','はっぱ','チューリップ','タンポポ'}
BUGS = {'カブトムシ','ダンゴムシ','アリ'}
PEOPLE = {'ママ','パパ','ベビー','ファミリー','ペット','おかあさん','おとうさん','あかちゃん','ともだち'}


def all_sentence_options(w: str, theme: int) -> list[dict]:
    """Thematic safe templates + reviewed exceptions; avoids mismatched verbs."""
    if w in PERSON_SPECIAL:
        return [entry(*line, emoji=WORDS[w]['emoji']) for line in SPECIAL.get(w, [])]
    modes = ['this']
    if theme==0: modes += ['like','eat','give','is_it']
    elif theme==1: modes += ['like','animate','see','is_it']
    elif theme==2: modes += ['like','give','drink' if w in DRINKS else 'eat','is_it']
    elif theme==3: modes += ['have','where','is_it']
    elif theme==4: modes = ['this','like','colorpen','colorlike','is_it']
    elif theme==5: modes += ['use','where','want','is_it']
    elif theme==6: modes += (['like','ride','where','is_it'] if w in VEHICLES else ['where','is_it'])
    elif theme==7: modes += (['look','pretty','is_it'] if w in {'そら','やま','うみ','かわ','くも'} else ['want','where','is_it'])
    elif theme==8: modes += (['like','is_it'] if w in {'ゲーム','アニメ','ダンス'} else ['like','want','is_it'])
    elif theme==9: modes += ['where','want','is_it']
    elif theme==10: modes += ['like','play','is_it'] if w not in {'いろ','かたち','ひも','えほん'} else ['where','is_it']
    elif theme==11: modes += ['like','give','drink' if w in DRINKS else 'simpleeat','is_it'] if w not in {'あじ','さとう'} else ['where','is_it']
    elif theme==12: modes += ['like','drink' if w in DRINKS else 'simpleeat','is_it']
    elif theme==13: modes += ['like','is_it']
    elif theme==14: modes += (['like','animate','where','is_it'] if w in PEOPLE-{'ファミリー'} else ['like','where','is_it'] if w=='ファミリー' else ['where','is_it'])
    elif theme==15: modes += (['where','go','is_it'] if w not in {'エレベーター','そと'} else ['where','is_it'])
    elif theme==16: modes += ['like','is_it']
    elif theme==17: modes += ['like','animate' if w in BUGS else 'have','see','is_it']
    elif theme==18: modes += ['like','is_it']
    else: modes += (['where','is_it'] if w in {'シール','ソース','しお'} else ['like','is_it'] if w in {'かぜ','なつ'} else ['like','look','is_it'] if w in {'つき','そら'} else ['like','is_it'])
    outs=[]
    for mode in dict.fromkeys(modes[:1]):
        outs.append(common(w,mode))
    for line in SPECIAL.get(w,[]):
        outs.append(entry(*line,emoji=WORDS[w]['emoji']))
    for mode in dict.fromkeys(modes[1:]):
        outs.append(common(w,mode))
    unique=[]; seen=set()
    for item in outs:
        if item['value'] not in seen:
            unique.append(item); seen.add(item['value'])
    return unique


def dialogues(words: list[str], day: int) -> list[dict]:
    """Simple A/B exchanges show particles and reply patterns, not quizzes for the learner."""
    candidates=[w for w in words if w not in PERSON_SPECIAL and w not in {'あじ','なまえ'}]
    rng=random.Random(day*1171+91); rng.shuffle(candidates)
    pairs=[]
    for word in candidates[:4]:
        w=WORDS[word]; rd=w['reading']; mn=w['meaning']
        pairs.extend([
            entry(f'これは{word}ですか？',f'코레와 {rd}데스카?',f'이것은 {mn}인가요?', '🗣️', 'dialogue'),
            entry(f'はい、{word}です',f'하이, {rd}데스',f'네, {mn}예요', '💬', 'dialogue')
        ])
    if day_index(day)==13:
        for q in [('げんきですか？','겡키데스카?','잘 지내나요?'),
                  ('はい、げんきです！','하이, 겡키데스!','네, 잘 지내요!')]:
            pairs.append(entry(*q,emoji='👋',kind='dialogue'))
    if day_index(day)==18:
        for q in [('きょうはげんき？','쿄-와 겡키?','오늘은 잘 지내?'),
                  ('うん、げんきだよ','응, 겡키다요','응, 잘 지내!')]:
            pairs.append(entry(*q,emoji='😊',kind='dialogue'))
    if day_index(day)==0:
        for q in [
            ('バナナをたべたい？','바나나오 타베타이?','바나나 먹고 싶어?'),
            ('うん、たべたい！','응, 타베타이!','응, 먹고 싶어!'),
            ('これはバナナ？','코레와 바나나?','이건 바나나야?'),
            ('うん、バナナだよ','응, 바나나다요','응, 바나나야'),
            ('バナナがすき？','바나나가 스키?','바나나 좋아해?'),
            ('うん、だいすき！','응, 다이스키!','응, 정말 좋아!')
        ]: pairs.append(entry(*q,emoji='🍌',kind='dialogue'))
    return pairs


def daily_content(day: int, config: dict|None=None) -> dict:
    if day < 1: raise ValueError('day must be positive')
    config=config or {}
    idx=day_index(day)
    previous = day_index(day-1) if day>1 else day_index(day+1)
    cycle=(day-1)//len(THEMES)
    primary=theme_words(idx,cycle)
    secondary=theme_words(previous,cycle if day==1 else max(0,(day-2)//len(THEMES)))
    # Today: 10 main-topic words, 10 companion words; plus up to N from earlier dates.
    older=[]
    for gap in [2,4,7,14,3,5,9,12,18,1]:
        prior=day-gap
        if prior < 1: continue
        for word in theme_words(day_index(prior), (prior-1)//len(THEMES)):
            if word not in primary and word not in secondary and word not in older: older.append(word)
    # First day still includes plenty of everyday words, but never mislabels them as reviews.
    if len(older)<int(config.get('extra_words',16)):
        for offset in range(2,19):
            for word in theme_words(day_index(day+offset), cycle):
                if word not in primary and word not in secondary and word not in older: older.append(word)
                if len(older)>=int(config.get('extra_words',16)):break
            if len(older)>=int(config.get('extra_words',16)):break
    take=int(config.get('extra_words',16))
    recent = older[:take]
    familiar=[]
    for word in primary+secondary:
        familiar.append(word_entry(word, 'word'))
    for word in recent:
        # On the first workday these are bonus words rather than previously learned ones.
        familiar.append(word_entry(word, 'review_word' if day>2 else 'word'))

    focus_sentences=[]
    for word in primary:
        focus_sentences.extend(all_sentence_options(word,idx)[:int(config.get('sentences_per_focus_word',4))])
    companion_sentences=[]
    for word in secondary:
        companion_sentences.extend(all_sentence_options(word,previous)[:int(config.get('sentences_per_companion_word',2))])
    # Original hand-authored examples introduce new words in contextual phrases.
    for theme_id in (idx,previous):
        for p in PHRASES[theme_id]:
            focus_sentences.append(entry(*p))
    review_sentences=[]
    for word in recent:
        m = next((i for i in range(len(THEMES)) if word in theme_words(i)), idx)
        options=all_sentence_options(word,m)
        review_sentences.extend(options[2:3] or options[:1])
    conversation=dialogues(primary,day)

    seen=set(); groups=[]
    # Do not multiply the same text in a day, except purposeful exposure via app's scrolling.
    for kind, group in [('word',familiar),('sentence',focus_sentences),('sentence',companion_sentences),
                        ('review_sentence',review_sentences),('dialogue',conversation)]:
        uniq=[]
        for obj in group:
            if obj['value'] in seen: continue
            item={**obj}; item['kind']=kind if obj['kind'] not in ('word','review_word') else obj['kind']
            # distinguish past practice without adding an instructional prompt
            if kind=='review_sentence':item['title']='🔁 '+item['title']
            seen.add(item['value']);uniq.append(item)
        groups.append(uniq)
    # Interleave the subgroups, so short words and examples alternate all day.
    items=[];round_no=0
    while any(groups):
        for i in range(len(groups)):
            group=groups[(i+round_no)%len(groups)]
            if group:items.append(group.pop(0))
        round_no+=1
    return {'day':day,'theme':THEMES[idx][0],'companion_theme':THEMES[previous][0],
            'title':f'{day}일차 · {THEMES[idx][0]} + 생활 문장', 'items':items,
            'word_count':sum(x['kind'] in ('word','review_word') for x in items),
            'sentence_count':sum(x['kind'] in ('sentence','review_sentence','dialogue') for x in items)}


def base_url() -> str:
    manual=os.environ.get('PAGES_BASE_URL','').rstrip('/')
    if manual:
        if not manual.startswith('https://'):raise ValueError('PAGES_BASE_URL should be HTTPS')
        return manual
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if '/' in repo:
        owner,name=repo.split('/',1)
        if name.lower()==f'{owner.lower()}.github.io': return f'https://{owner.lower()}.github.io'
        return f'https://{owner.lower()}.github.io/{name}'
    return 'https://example.org/jp-kana-ticker'  # preview, not deployed


def rss_xml(now:datetime,lesson:dict,site:str, kinds:tuple[str,...]|None=None) -> bytes:
    items=[(n,v) for n,v in enumerate(lesson['items'],1) if kinds is None or v['kind'] in kinds]
    rss=ET.Element('rss',{'version':'2.0'})
    channel=ET.SubElement(rss,'channel')
    name='일본어 놀이터 · 그림 단어에서 생활 문장까지'
    if kinds == ('word','review_word'):name+=' / 단어만'
    elif kinds is not None:name+=' / 문장만'
    metadata={'title':name, 'link':site+'/', 'description':f"{lesson['title']} | 단어 {lesson['word_count']}개, 문장 {lesson['sentence_count']}개 | 평일마다 변경",
              'language':'ko-KR','lastBuildDate':format_datetime(now.astimezone(timezone.utc)),'ttl':'60'}
    for k,v in metadata.items():ET.SubElement(channel,k).text=str(v)
    for seq,(n,it) in enumerate(items,1):
        node=ET.SubElement(channel,'item')
        ET.SubElement(node,'title').text=it['title']
        ET.SubElement(node,'link').text=f'{site}/#item-{n}'
        ET.SubElement(node,'guid',{'isPermaLink':'false'}).text=f'jpplay:v4:{lesson["day"]}:{n}:{it["value"]}'
        ET.SubElement(node,'description').text=f"{it['value']} / {it['reading']} / {it['meaning']}"
        ET.SubElement(node,'pubDate').text=format_datetime((now-timedelta(seconds=seq)).astimezone(timezone.utc))
    ET.indent(rss,space='  ')
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)


def html_page(now:datetime,lesson:dict,weekend:bool) -> str:
    cards=[]
    labels={'word':'그림 단어','review_word':'복습 단어','sentence':'생활 문장','review_sentence':'복습 문장','dialogue':'짧은 대화'}
    for n,it in enumerate(lesson['items'],1):
        cards.append(f'''<article class="card" id="item-{n}"><div class="tag">{escape(labels[it['kind']])}</div>
        <div class="jp">{escape(it['emoji'])} {escape(it['value'])}</div>
        <div class="kr">{escape(it['reading'])}</div><div class="meaning">{escape(it['meaning'])}</div>
        <button type="button" class="speak" data-jp="{escape(it['value'],quote=True)}">🔊 일본어 듣기</button></article>''')
    weekend_note=' · 주말에는 마지막 평일의 진도를 유지합니다' if weekend else ''
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>일본어 놀이터 | {lesson['day']}일차</title><link rel="alternate" href="rss.xml" type="application/rss+xml">
    <style>*{{box-sizing:border-box}}body{{margin:0;background:#f7f8fb;color:#1e293b;font-family:"Malgun Gothic","Yu Gothic",system-ui,sans-serif}}
    main{{max-width:1220px;margin:auto;padding:32px 18px 60px}}header{{border-radius:22px;background:white;padding:28px;border:1px solid #e5e7eb}}
    h1{{font-size:clamp(1.65rem,4vw,2.5rem);margin:.1em 0}}p{{line-height:1.7}}.meta{{color:#64748b;font-size:.95rem}}
    .feeds{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}}.feeds a{{padding:8px 12px;border-radius:10px;background:#e8efff;color:#164c9b;text-decoration:none;font-weight:700}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:13px;margin-top:22px}}
    .card{{background:white;border-radius:17px;padding:15px;border:1px solid #e2e8f0;min-height:189px}}
    .tag{{font-size:.78rem;color:#64748b}}.jp{{font-size:1.45rem;font-weight:800;line-height:1.45;margin:10px 0}}
    .kr{{color:#475569;font-weight:650}}.meaning{{color:#64748b;margin:3px 0 12px}}button{{background:#f1f5f9;border:1px solid #cbd5e1;border-radius:9px;padding:7px 10px;cursor:pointer}}
    footer{{margin-top:24px;color:#64748b;font-size:.86rem}}@media (max-width:640px){{.jp{{font-size:1.3rem}}}}</style></head><body><main>
    <header><h1>🎈 일본어 놀이터 — {lesson['day']}일차</h1><p><strong>{escape(lesson['theme'])}</strong> · 함께 복습: {escape(lesson['companion_theme'])}</p>
    <p>낱글자 암기 없이, 쉬운 단어 → 짧은 문장 → 질문과 대답으로 이어지는 초급 일본어입니다. 업무 중에는 티커를 가볍게 읽고, 여기서는 발음도 들어보세요.</p>
    <div class="meta">단어 {lesson['word_count']}개 · 문장/대화 {lesson['sentence_count']}개 · 기준 {now.strftime('%Y-%m-%d %H:%M')} KST{weekend_note}</div>
    <nav class="feeds"><a href="rss.xml">📡 전체 RSS</a><a href="rss-words.xml">🍎 단어만</a><a href="rss-sentences.xml">💬 문장만</a></nav></header>
    <section class="grid">{''.join(cards)}</section><footer>한국어 발음은 근사 표기이며 실제 일본어 소리와 차이가 있습니다. 조사 は는 ‘와’, を는 ‘오’처럼 발음됩니다. 음성 듣기는 브라우저·운영체제의 일본어 음성 지원 여부에 따릅니다. 진도는 주말을 제외한 달력 기준이며 숙달도는 측정하지 않습니다.</footer>
    </main><script>document.querySelectorAll('.speak').forEach(b=>b.addEventListener('click',()=>{{if(!('speechSynthesis' in window))return alert('음성 합성 미지원');const u=new SpeechSynthesisUtterance(b.dataset.jp);u.lang='ja-JP';u.rate=.82;const v=speechSynthesis.getVoices().find(x=>x.lang.toLowerCase().startsWith('ja'));if(v)u.voice=v;speechSynthesis.cancel();speechSynthesis.speak(u);}}));</script></body></html>'''


def generate(on_date:date, config:dict|None=None) -> dict:
    settings=config or json.loads(CONF.read_text(encoding='utf-8'))
    zone=ZoneInfo(settings.get('timezone','Asia/Seoul'))
    now=datetime.combine(on_date,time(7,17),tzinfo=zone)
    day=learning_day(on_date,date.fromisoformat(settings['start_date']))
    lesson=daily_content(day,settings);site=base_url();DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'rss.xml').write_bytes(rss_xml(now,lesson,site))
    (DEST/'rss-words.xml').write_bytes(rss_xml(now,lesson,site,('word','review_word')))
    (DEST/'rss-sentences.xml').write_bytes(rss_xml(now,lesson,site,('sentence','review_sentence','dialogue')))
    (DEST/'index.html').write_text(html_page(now,lesson,on_date.weekday()>4),encoding='utf-8')
    (DEST/'.nojekyll').touch()
    return lesson


def main() -> None:
    parser=argparse.ArgumentParser(description='Generate daily Japanese play RSS')
    parser.add_argument('--date',help='Preview YYYY-MM-DD (Asia/Seoul)')
    args=parser.parse_args()
    d=date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo('Asia/Seoul')).date()
    lesson=generate(d)
    print(f'{d} | study day {lesson["day"]} | total {len(lesson["items"])} | words {lesson["word_count"]} / phrases {lesson["sentence_count"]} | {base_url()}')

if __name__=='__main__':main()
