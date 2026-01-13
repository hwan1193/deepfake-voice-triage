# deepfake-voice-triage
 Deepfake Voice Triage (Heuristic) + Verify Protocol Bot

가족/지인 대상 “보이스피싱·딥페이크 의심 콜” 상황에서,
1) 음성 파일을 표준 포맷(16kHz mono WAV)으로 변환하고  
2) 휴리스틱 기반 참고 점수로 1차 triage를 하고  
3) 최종 확정은 **콜백 + 세이프워드(가족 합의 질문)** 로 처리하는 프로토콜을 제공합니다.

> ⚠️ 이 프로젝트는 “딥페이크 확정 판정기”가 아닙니다.  
> 자동 점수는 참고용이며, 최종 검증은 콜백/세이프워드가 정답입니다.

---

## Workflow

1. (입력) 휴대폰 음성: `.m4a` (AAC 등)
2. (변환) `ffmpeg`로 `16kHz/mono/PCM WAV` 생성
3. (분석) `voice_deepfake_heuristic.py`로 점수/특성값 출력
4. (대응) 의심 상황이면:
   - 통화 즉시 종료
   - 저장된 번호로 콜백
   - 세이프워드 질문
   - 금전/앱설치/인증요구는 112/118

---

## Requirements

- Rocky/EL9 계열 + ffmpeg/ffprobe
- Python 3.9+ (venv 권장)
- (옵션) Telegram Bot API / SMTP 릴레이 (사내 정책에 따라 제한될 수 있음)

---

## Convert audio (m4a -> wav)

```bash
ffmpeg -y -i mom_voice.m4a -vn -ac 1 -ar 16000 -c:a pcm_s16le input_16k_mono.wav
ffprobe -hide_banner -show_streams -select_streams a:0 input_16k_mono.wav | egrep "codec_name|sample_rate|channels|duration"

## 실행 방법 ##

cd /root/deepfake_test
source .venv/bin/activate
python voice_deepfake_heuristic.py /path/to/input_16k_mono.wav
==============================================================================
(Result interpretation / 결과 해석) :

Score: 0~100

낮다고 “진짜” 확정 아님

짧은 음성/잡음/코덱/최신 TTS는 탐지를 흔들 수 있음
=============================================================================
(Verify protocol (Telegram)) :

사내망 정책으로 API 차단/토큰 제한이 있을 수 있음.

export TG_BOT_TOKEN="..."
export TG_CHAT_ID="-100..."
python3 scripts/call_verify_bot.py --from-num 01000000000 --who "엄마" --summary "검사 사칭 + 급전 요구"
==================================================================================================================
# Troubleshooting

-h 옵션 에러:

이 스크립트는 argparse 도움말이 없고 첫 인자를 파일 경로로 처리함.

Telegram 401 Unauthorized:

토큰 자체가 invalid/폐기/오타 가능성이 큼.

SMTP Name or service not known:

DNS에 해당 호스트 없음

SMTP timed out:

방화벽/ACL/포트 리슨 여부 확인 필요
