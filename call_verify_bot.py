#!/usr/bin/env python3
"""
call_verify_bot.py
- 의심 전화/문자 상황을 가족 단체방(텔레그램)으로 즉시 공유 + 인증 절차 안내
- 딥페이크 판정이 아니라, '확정 인증' 프로토콜을 자동화하는 목적
Usage:
  export TG_BOT_TOKEN="xxxx"
  export TG_CHAT_ID="-1001234567890"   # 그룹/채널 chat id
  python call_verify_bot.py --from-num 01058113247 --summary "서울지검/급전 요구"
"""

import os
import json
import argparse
import datetime
import urllib.request

SAFE_WORD_HINT = "세이프워드 질문: '우리 집 냉장고 2번째 칸 뭐였지?'"  # 가족끼리만 아는 질문으로 교체

def tg_send(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-num", dest="from_num", required=True, help="발신 번호")
    ap.add_argument("--summary", dest="summary", required=True, help="상황 요약")
    ap.add_argument("--who", dest="who", default="(미상)", help="상대가 주장한 인물")
    args = ap.parse_args()

    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Missing TG_BOT_TOKEN or TG_CHAT_ID env vars.")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"보이스피싱/딥페이크 의심 콜\n"
        f"- 시간: {now}\n"
        f"- 발신: {args.from_num}\n"
        f"- 상대 주장: {args.who}\n"
        f"- 요약: {args.summary}\n\n"
        f"인증 절차(확정)\n"
        f"1) 지금 통화는 끊고, 저장된 번호로 콜백\n"
        f"2) {SAFE_WORD_HINT}\n"
        f"3) 돈/인증/앱설치 요구는 즉시 112/118 신고\n"
    )
    tg_send(token, chat_id, msg)
    print("OK: alert sent")

if __name__ == "__main__":
    main()
