# 🎈 일본어 놀이터 5.0 — 단어는 훨씬 많이, 문장은 더 다양하게

Taskbar Ticker에서 **히라가나·가타카나 단어와 실제 생활에서 쓰는 짧은 일본어 문장**을 반복 노출합니다. 글자 하나씩 외우기, 읽어볼까요?, 동일 문형 복제는 사용하지 않습니다.

## 학습 분량과 운영 방식

- **전체 단어은행: 555개** (기존 약 194개 + 새 단어 361개)
- **매 평일 단어: 중복 없는 100개**. 이는 *그날 화면에 등장하는 서로 다른 단어 수*로, 전부 처음 나오는 단어라는 뜻은 아닙니다.
- **매 평일 생활 표현: 서로 다른 55개**. 직접 검토해 작성한 총 220개의 상황별 문장·대화 표현을 여러 주제에서 골라 섞습니다. 똑같은 문형에 명사만 바꾸는 방식은 사용하지 않습니다.
- 가타카나 단어와 히라가나 단어를 균형 있게 섞고, 날마다 핵심 주제 + 주변 주제 + 지나간 주제에서 가져와 반복합니다.
- 모든 항목에 **일본어 · 한국어 발음(근사값) · 한국어 뜻**을 표기합니다.
- 진도 기준일: **2026-10-23(금), 1일차**.
- 월~금 오전 **7:17 KST** 새 진도 자동 발행. 토·일은 금요일 진도를 유지합니다. GitHub 예약 작업은 지연될 수 있습니다.

**예시**
```text
🍎 あかいりんごをひとつください (아카이 링고오 히토츠 쿠다사이) · 빨간 사과 하나 주세요
🐶 いぬとさんぽにいこう (이누토 산포니 이코-) · 강아지와 산책 가자
🍌 バナナ (바나나) · 바나나
🏠 へや (헤야) · 방
🎧 イヤホン (이야혼) · 이어폰
☀️ きょうはいいてんきだね (쿄-와 이이 텐키다네) · 오늘 날씨 좋네
```

## RSS 주소

- **전체(권장)**: https://jeryoma.github.io/jp-kana-ticker/rss.xml
- **단어만**: https://jeryoma.github.io/jp-kana-ticker/rss-words.xml
- **문장만**: https://jeryoma.github.io/jp-kana-ticker/rss-sentences.xml
- **학습 페이지 및 일본어 음성 듣기**: https://jeryoma.github.io/jp-kana-ticker/

기존 사용자는 **Taskbar Ticker의 RSS 주소를 변경할 필요가 없습니다**. GitHub Pages에 새 RSS가 배포되고 앱이 다시 읽으면 자동으로 적용됩니다.

## 파일 안내

- `play_v5.py`: 100개 고유 단어 + 55개 상황 문장 생성기 (**현재 실제 자동 배포에 사용**)
- `expanded_vocab_v5.py`: 추가 단어 361개 (20주제)
- `scenes_v5.py`: 문장·회화 표현 220개 (20주제 + 공통)
- `learning_data.py`: 기본 단어 자료 (기존 내용 보존)
- `generate.py`: 이전 버전과 RSS/웹페이지 생성 공통 함수 (이전 버전 호환성 유지)
- `config.json`: 학습 시작일과 하루 분량
- `tests/test_v5.py`: 기본 220일 분량의 고유 단어 수·문장 수·가나 균형·RSS 형식 검사
- `.github/workflows/publish.yml`: GitHub Pages 자동 배포
- `docs/`: 최종 배포되는 RSS·학습 페이지

## 진도와 분량 변경

`config.json`:
```json
{
  "start_date": "2026-10-23",
  "timezone": "Asia/Seoul",
  "daily_unique_words": 100,
  "daily_varied_sentences": 55
}
```
기존 버전 호환을 위한 다른 설정 값은 남겨 두어도 괜찮습니다. 실제 새 버전에서 사용하는 하루 분량 키는 `daily_unique_words`(50~555), `daily_varied_sentences`(20~65)입니다.

## 점검 및 배포

```bash
python -m unittest discover -s tests -v
python play_v5.py --date 2026-10-23
```

GitHub `Actions → Publish Japanese word-and-sentence RSS`에서 `build`, `deploy`가 모두 성공했는지 확인하세요. GitHub Pages가 갱신되면 앱에서 새 RSS를 다시 불러올 수 있습니다. 브라우저 음성 읽기는 사용하는 기기의 일본어 TTS 지원에 따라 달라집니다.

**참고:** 한글 발음은 일본어 원어민의 실제 소리를 정확히 옮기지 못합니다. 실제 발음은 학습 페이지의 듣기 기능으로 확인하는 것이 좋습니다.
