"""
AI 로직 (Person 4 담당).

GEMINI_API_KEY가 .env에 설정돼 있으면 실제 Gemini로 동작하고,
아직 키가 없으면 간단한 키워드 규칙으로 자동 대체(fallback)해서 동작한다.
-> 즉 API 키 세팅 전에도 앱 전체가 바로 돌아간다. 키를 넣는 순간부터 AI 정확도가 올라감.
"""

import os
import re
from datetime import date, timedelta
from typing import Optional, List

from pydantic import BaseModel

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL_NAME = "gemini-3.5-flash"

_client = None
_gemini_ready = False

if GEMINI_API_KEY:
    try:
        from google import genai
        from google.genai import types

        _client = genai.Client(api_key=GEMINI_API_KEY)
        _gemini_ready = True
    except Exception as e:  # 패키지 미설치 등, 앱이 죽지 않게 방어
        print(f"[ai_service] Gemini 초기화 실패, 규칙 기반 모드로 대체: {e}")
        _gemini_ready = False
else:
    print("[ai_service] GEMINI_API_KEY가 없어서 규칙 기반(fallback) 모드로 실행 중. "
          ".env에 키를 넣으면 실제 Gemini로 업그레이드됨.")


class TaskDetection(BaseModel):
    is_task: bool
    title: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# 규칙 기반 fallback (API 키 없어도 데모가 돌아가게)
# ---------------------------------------------------------------------------

_CHORE_KEYWORDS = ["청소", "설거지", "쓰레기", "빨래", "분리수거", "화장실", "정리", "쓸어", "닦아"]


def _rule_based_detect(message: str, sender_name: str) -> TaskDetection:
    hit = any(k in message for k in _CHORE_KEYWORDS)
    if not hit:
        return TaskDetection(is_task=False, confidence=0.3)

    title = next((k for k in _CHORE_KEYWORDS if k in message), "할일")
    due = date.today().isoformat()
    if "내일" in message:
        due = (date.today() + timedelta(days=1)).isoformat()
    elif "주말" in message:
        days_ahead = (5 - date.today().weekday()) % 7  # 다음 토요일
        due = (date.today() + timedelta(days=days_ahead or 7)).isoformat()

    return TaskDetection(is_task=True, title=title, assignee=None, due_date=due, confidence=0.6)


def _rule_based_summary(room: "RoomStatus") -> str:
    lines = []
    if room.rent_due_date:
        lines.append(f"💰 월세 마감일: {room.rent_due_date} ({room.rent_amount or '금액 미정'})")
    if room.pending_chores:
        lines.append(f"🧹 아직 안 끝난 할일: {', '.join(room.pending_chores)}")
    else:
        lines.append("🧹 남은 할일 없음, 다들 잘하고 있어요!")
    if room.completed_chores_today:
        lines.append(f"✅ 오늘 완료: {', '.join(room.completed_chores_today)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 공개 함수: main.py에서는 이 두 개만 호출하면 됨
# ---------------------------------------------------------------------------

def detect_task(message: str, sender_name: str = "") -> dict:
    if not _gemini_ready:
        return _rule_based_detect(message, sender_name).model_dump()

    today = date.today().isoformat()
    prompt = f"""너는 룸메이트 채팅방의 메시지를 분석해서 '할일(chore)'인지 판단하는 도우미야.

오늘 날짜: {today}
보낸 사람: {sender_name or "알 수 없음"}
메시지: "{message}"

청소, 설거지, 쓰레기 버리기, 월세 관련 등 룸메이트끼리 해야 할 일을 제안/지시하는
내용이면 is_task를 true로, 잡담이면 false로 해줘. 날짜가 언급돼 있으면 오늘 날짜
기준으로 YYYY-MM-DD로 변환해줘. 담당자가 명시 안 됐으면 assignee는 null."""

    try:
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=TaskDetection.model_json_schema(),
            ),
        )
        return TaskDetection.model_validate_json(response.text).model_dump()
    except Exception as e:
        print(f"[ai_service] Gemini 호출 실패, 이번 요청은 규칙 기반으로 대체: {e}")
        return _rule_based_detect(message, sender_name).model_dump()


class RoomStatus(BaseModel):
    rent_due_date: Optional[str] = None
    rent_amount: Optional[str] = None
    pending_chores: List[str] = []
    completed_chores_today: List[str] = []


def daily_summary(room: RoomStatus) -> str:
    if not _gemini_ready:
        return _rule_based_summary(room)

    prompt = f"""너는 룸메이트 공유 앱의 '오늘의 요약'을 작성하는 친근한 도우미야.
아래 정보로 2~4문장짜리 짧고 친근한 한국어 요약을 작성해줘. 이모지 1~2개 정도 사용 가능.

월세 마감일: {room.rent_due_date or "정보 없음"}
월세 금액: {room.rent_amount or "정보 없음"}
아직 안 끝난 할일: {", ".join(room.pending_chores) if room.pending_chores else "없음"}
오늘 완료된 할일: {", ".join(room.completed_chores_today) if room.completed_chores_today else "없음"}
"""
    try:
        response = _client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[ai_service] Gemini 호출 실패, 규칙 기반 요약으로 대체: {e}")
        return _rule_based_summary(room)
