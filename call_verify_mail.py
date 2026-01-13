#!/usr/bin/env python3
"""
call_verify_mail.py
- 보이스피싱/딥페이크 의심 상황을 "메일"로 즉시 공유
- 판정이 아니라 '확정 인증' 프로토콜 안내 목적

ENV (필수/선택)
  SMTP_HOST        : smtp.corp.local OR smtp.office365.com
  SMTP_PORT        : 25 / 587 / 465
  SMTP_FROM        : dy.p***@tr***.com
  SMTP_TO          : "dy.p***@tr***.com;someone@tr***.com"
  SMTP_CC          : optional
  SMTP_BCC         : optional
  SMTP_USER        : optional (Office365면 보통 필요)
  SMTP_PASS        : optional (Office365면 보통 필요)
  SMTP_STARTTLS    : true/false  (587에서 true)
  SMTP_SSL         : true/false  (465에서 true)
  SMTP_TIMEOUT     : seconds (default 10)
  DRYRUN           : true/false

Usage:
  python3 call_verify_mail.py --from-num 010... --who "엄마" --summary "검사 사칭 + 급전 요구"
"""

import os
import ssl
import argparse
import datetime
import smtplib
import socket
from email.message import EmailMessage

SAFE_WORD_HINT = "세이프워드 질문: '우리 집 냉장고 2번째 칸 뭐였지?'"  # 가족끼리만 아는 질문으로 교체


def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def split_addrs(s: str):
    if not s:
        return []
    # 세미콜론/콤마 모두 허용
    parts = []
    for token in s.replace(",", ";").split(";"):
        t = token.strip()
        if t:
            parts.append(t)
    return parts


def dns_check(host: str) -> str:
    try:
        socket.getaddrinfo(host, None)
        return "OK"
    except socket.gaierror as e:
        return f"FAIL ({e})"


def send_mail(subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "25"))
    smtp_from = os.getenv("SMTP_FROM", "").strip()
    smtp_to = os.getenv("SMTP_TO", "").strip()
    smtp_cc = os.getenv("SMTP_CC", "").strip()
    smtp_bcc = os.getenv("SMTP_BCC", "").strip()

    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()

    starttls = env_bool("SMTP_STARTTLS", False)
    use_ssl = env_bool("SMTP_SSL", False)
    timeout = int(os.getenv("SMTP_TIMEOUT", "10"))
    dryrun = env_bool("DRYRUN", False)

    if not smtp_host or not smtp_from or not smtp_to:
        raise SystemExit("Missing required env vars: SMTP_HOST, SMTP_FROM, SMTP_TO")

    # DNS 체크(운영 로그용)
    dns_status = dns_check(smtp_host)

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = ", ".join(split_addrs(smtp_to))
    if smtp_cc:
        msg["Cc"] = ", ".join(split_addrs(smtp_cc))
    if smtp_bcc:
        # EmailMessage는 Bcc 헤더를 넣어도 되지만, 통상 헤더 숨김용으로 sendmail에만 반영
        pass
    msg["Subject"] = subject

    msg.set_content(
        body
        + "\n\n[SMTP Diagnostics]\n"
        + f"- SMTP_HOST: {smtp_host}\n"
        + f"- DNS: {dns_status}\n"
        + f"- PORT: {smtp_port}\n"
        + f"- STARTTLS: {starttls}\n"
        + f"- SSL: {use_ssl}\n"
    )

    rcpt = split_addrs(smtp_to) + split_addrs(smtp_cc) + split_addrs(smtp_bcc)

    if dryrun:
        print("[DRYRUN] Would send mail:")
        print(msg)
        print("[DRYRUN] Recipients:", rcpt)
        return

    context = ssl.create_default_context()

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout, context=context) as s:
            s.ehlo()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg, from_addr=smtp_from, to_addrs=rcpt)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as s:
            s.ehlo()
            if starttls:
                s.starttls(context=context)
                s.ehlo()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg, from_addr=smtp_from, to_addrs=rcpt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-num", required=True, help="발신 번호")
    ap.add_argument("--summary", required=True, help="상황 요약 (예: 검사 사칭/급전/앱설치 유도 등)")
    ap.add_argument("--who", default="(미상)", help="상대가 주장한 인물(엄마/아빠/동생/본인 등)")
    args = ap.parse_args()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[보이스피싱/딥페이크 의심] {args.who} 주장 / {args.from_num}"

    body = (
        "보이스피싱/딥페이크 의심 콜\n"
        f"- 시간: {now}\n"
        f"- 발신: {args.from_num}\n"
        f"- 상대 주장: {args.who}\n"
        f"- 요약: {args.summary}\n\n"
        "인증 절차(확정)\n"
        "1) 지금 통화는 끊고, 저장된 번호로 콜백\n"
        f"2) {SAFE_WORD_HINT}\n"
        "3) 돈/인증/앱설치 요구는 즉시 112/118 신고\n"
    )

    try:
        send_mail(subject, body)
        print("OK: mail sent")
        return 0
    except Exception as e:
        # PowerShell 스크립트처럼 로컬 로그 남김
        logp = os.getenv("MAIL_ERROR_LOG", "/root/deepfake_test/mail_error.log")
        with open(logp, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - MailError - {repr(e)}\n")
        print(f"ERROR: failed to send mail ({e})")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
