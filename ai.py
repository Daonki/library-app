from openai import OpenAI
import streamlit as st
import pandas as pd


def get_client():
    """OpenAI 클라이언트 — Streamlit Secrets에서 키 로드"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        raise ValueError(
            "OpenAI API 키가 설정되지 않았습니다.\n"
            "Streamlit Cloud → Settings → Secrets에 아래 내용을 추가해주세요:\n"
            'OPENAI_API_KEY = "sk-..."'
        )
    return OpenAI(api_key=api_key)


def build_context(df_merged: pd.DataFrame, df_seat: pd.DataFrame = None) -> str:
    """GPT에 넘길 도서관 현황 컨텍스트 생성 (열람실 상세 포함)"""
    lines = []
    for _, row in df_merged.iterrows():
        open_t = str(row["wkdyOperBgngTm"]).zfill(6)
        close_t = str(row["wkdyOperEndTm"]).zfill(6)
        open_str = f"{open_t[:2]}:{open_t[2:4]}"
        close_str = f"{close_t[:2]}:{close_t[2:4]}"
        oper = row.get("operSttsNm", "")
        oper_str = f", 운영상태={oper}" if oper else ""

        clsr = str(row.get("clsrInfoExpln", "")).strip()
        clsr_str = f", 휴관일={clsr}" if clsr and clsr != "nan" else ""

        lib_line = (
            f"- {row['pblibNm']} ({row['ctpvNm']} {row['sggNm']}): "
            f"잔여 {int(row['rmnd_seats'])}/{int(row['total_seats'])}석, "
            f"혼잡도={row['status']}, 운영시간={open_str}~{close_str}{oper_str}{clsr_str}"
        )

        # 열람실 상세 추가
        if df_seat is not None:
            rooms = df_seat[df_seat["pblibNm"] == row["pblibNm"]]
            if len(rooms) > 0:
                room_lines = []
                for _, r in rooms.iterrows():
                    room_lines.append(
                        f"  · {r['rdrmNm']} ({r.get('rdrmTypeNm','일반')}): "
                        f"잔여 {int(r['rmndSeatCnt'])}/{int(r['tseatCnt'])}석"
                    )
                lib_line += "\n" + "\n".join(room_lines)

        lines.append(lib_line)
    return "\n".join(lines)


def ask_ai(question: str, df_merged: pd.DataFrame) -> str:
    """사용자 질문에 대해 GPT가 도서관 추천"""
    client = get_client()
    context = build_context(df_merged)

    system_prompt = """당신은 공공도서관 열람실 안내 AI입니다.
실시간 잔여석 데이터를 바탕으로 사용자에게 가장 적합한 도서관을 추천해주세요.
답변은 한국어로 친절하고 간결하게 작성하고, 추천 이유와 잔여석 정보를 포함해주세요.
데이터에 없는 정보는 지어내지 마세요."""

    user_prompt = f"""현재 전국 공공도서관 열람실 실시간 현황입니다:

{context}

사용자 질문: {question}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content


def ask_ai_chat(chat_history: list, df_merged, df_seat=None) -> str:
    """대화 히스토리 전체를 GPT에 넘겨서 이어서 대화"""
    from datetime import datetime
    client = get_client()
    context = build_context(df_merged, df_seat)

    now = datetime.now()
    hour = now.hour
    weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    time_context = f"현재 시각: {now.strftime('%Y년 %m월 %d일')} ({weekday}요일) {hour}시"

    if 7 <= hour < 10:
        time_hint = "오전 이른 시간대라 대부분의 도서관이 한산한 편이에요."
    elif 10 <= hour < 13:
        time_hint = "오전 중반대로 학생과 직장인들이 몰리기 시작하는 시간이에요."
    elif 13 <= hour < 15:
        time_hint = "점심 이후 시간대로 혼잡도가 높아지는 경향이 있어요."
    elif 15 <= hour < 18:
        time_hint = "오후 시간대로 하루 중 가장 혼잡한 편이에요."
    elif 18 <= hour < 21:
        time_hint = "저녁 시간대로 직장인들이 합류해 혼잡할 수 있어요."
    else:
        time_hint = "늦은 시간대로 운영 중인 도서관이 제한적이에요."

    # 운영시간 마감까지 남은 시간 계산
    def calc_remaining(close_str):
        try:
            close_h = int(str(close_str).zfill(6)[:2])
            close_m = int(str(close_str).zfill(6)[2:4])
            remaining = (close_h * 60 + close_m) - (now.hour * 60 + now.minute)
            if remaining < 0:
                return -1
            return remaining
        except:
            return -1

    # 지금 당장 갈 수 있는 도서관 목록 (2시간 이상 남은 곳)
    available_libs = []
    for _, row in df_merged.iterrows():
        remaining = calc_remaining(row.get("wkdyOperEndTm", "0"))
        if remaining >= 120:
            available_libs.append(f"{row['pblibNm']} (마감까지 {remaining//60}시간 {remaining%60}분)")
    available_str = "\n".join(available_libs[:20]) if available_libs else "현재 2시간 이상 운영 가능한 도서관 정보 없음"
    
    system_prompt = f"""당신은 전국 공공도서관 열람실 안내 AI입니다.
실시간 잔여석 데이터를 바탕으로 사용자에게 가장 적합한 도서관을 추천하고 질문에 답변하세요.
답변은 한국어로 친절하고 간결하게 작성하고, 추천 이유와 잔여석 정보를 포함해주세요.
이전 대화 내용을 기억하고 자연스럽게 이어서 대화하세요.
데이터에 없는 정보는 지어내지 마세요.

{time_context}
시간대 특성: {time_hint}

[운영시간 안내]
지금 당장 방문 가능한 도서관 (마감까지 2시간 이상):
{available_str}

[공부 목적별 추천 기준]
- "혼자 조용히 공부" → 개인학습실 있고 혼잡도 여유인 곳 우선 추천
- "그룹 스터디" → 총좌석 수 많고 일반열람실 넓은 곳 추천
- "잠깐 공부" → 가까운 곳 중 잔여석 있는 곳 추천
- "오래 공부" → 마감 시간 늦고 잔여석 여유로운 곳 추천

[도서관 비교 요청시]
두 도서관을 비교할 때는 아래 항목을 표 형태로 정리해서 답변하세요:
- 혼잡도, 잔여석/총좌석, 운영시간, 휴관일, 열람실 수
- 각 열람실별 잔여석도 함께 표시해주세요.

현재 전국 공공도서관 열람실 실시간 현황:
{context}"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600
    )

    return response.choices[0].message.content