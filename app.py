import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from datetime import datetime

from api import fetch_library_info, fetch_seat_info, fetch_oper_status, build_merged_df, fmt_time, fmt_tel, get_room_detail, get_freshness
from ai import ask_ai, ask_ai_chat

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="도서관 찾자",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
.status-여유  { color: #1D9E75; font-weight: bold; }
.status-보통  { color: #BA7517; font-weight: bold; }
.status-혼잡  { color: #E24B4A; font-weight: bold; }
.metric-box   { background: #f8f9fa; border-radius: 8px; padding: 12px 16px; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 (캐시 5분) ───────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    df_info = fetch_library_info()
    df_seat = fetch_seat_info()
    df_prst = fetch_oper_status(df_info)
    df_merged = build_merged_df(df_info, df_seat, df_prst)
    return df_info, df_seat, df_merged

# ── 헤더 ────────────────────────────────────────────────────
st.title("📚 도서관 찾자")
st.caption("전국 공공도서관 열람실 실시간 잔여석 현황 · 공공데이터포털 API 기반")

with st.spinner("실시간 데이터 불러오는 중..."):
    df_info, df_seat, df_merged = load_data()

updated_at = datetime.now().strftime("%H:%M:%S")

# ── 요약 지표 ────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 도서관", f"{len(df_merged)}개")
col2.metric("여유 🟢", f"{(df_merged['status'] == '여유').sum()}개")
col3.metric("보통 🟡", f"{(df_merged['status'] == '보통').sum()}개")
col4.metric("혼잡 🔴", f"{(df_merged['status'] == '혼잡').sum()}개")

st.caption(f"마지막 업데이트: {updated_at}  |  5분마다 자동 갱신")



# ── 핵심 통계 카드 ──────────────────────────────────────────
total_rmnd = int(df_merged["rmnd_seats"].sum())
total_seats_all = int(df_merged["total_seats"].sum())
avg_usage = int(df_merged["ratio"].mean() * 100)

if "operSttsNm" in df_merged.columns:
    open_cnt = int((df_merged["operSttsNm"] == "운영중").sum())
    close_cnt = int((df_merged["operSttsNm"] == "휴관").sum())
else:
    open_cnt = len(df_merged)
    close_cnt = 0

region_avg = df_merged.groupby("ctpvNm")["ratio"].mean()
most_free = region_avg.idxmin()
most_free_pct = int(region_avg.min() * 100)
most_crowded = region_avg.idxmax()
most_crowded_pct = int(region_avg.max() * 100)

stat_cols = st.columns(4)
with stat_cols[0]:
    st.markdown(f"""
    <div style='background:#f8faff;border:1px solid #dde8f7;border-radius:12px;padding:16px;'>
      <div style='font-size:12px;color:#888;margin-bottom:6px'>전국 잔여석</div>
      <div style='font-size:22px;font-weight:700;color:#185FA5'>{total_rmnd:,}석</div>
      <div style='font-size:12px;color:#aaa;margin-top:4px'>총 {total_seats_all:,}석 중</div>
      <div style='margin-top:8px;background:#f0f0f0;border-radius:6px;height:5px'>
        <div style='background:#185FA5;height:5px;border-radius:6px;width:{int(total_rmnd/total_seats_all*100)}%'></div>
      </div>
    </div>""", unsafe_allow_html=True)

with stat_cols[1]:
    st.markdown(f"""
    <div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;'>
      <div style='font-size:12px;color:#888;margin-bottom:6px'>지금 운영중</div>
      <div style='font-size:22px;font-weight:700;color:#1D9E75'>{open_cnt}개</div>
      <div style='font-size:12px;color:#aaa;margin-top:4px'>휴관 {close_cnt}개 포함 총 {len(df_merged)}개</div>
    </div>""", unsafe_allow_html=True)

with stat_cols[2]:
    st.markdown(f"""
    <div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;'>
      <div style='font-size:12px;color:#888;margin-bottom:6px'>가장 여유로운 지역</div>
      <div style='font-size:20px;font-weight:700;color:#1D9E75'>{most_free}</div>
      <div style='font-size:12px;color:#aaa;margin-top:4px'>평균 사용률 {most_free_pct}%</div>
    </div>""", unsafe_allow_html=True)

with stat_cols[3]:
    st.markdown(f"""
    <div style='background:#fff5f5;border:1px solid #fecaca;border-radius:12px;padding:16px;'>
      <div style='font-size:12px;color:#888;margin-bottom:6px'>가장 혼잡한 지역</div>
      <div style='font-size:20px;font-weight:700;color:#E24B4A'>{most_crowded}</div>
      <div style='font-size:12px;color:#aaa;margin-top:4px'>평균 사용률 {most_crowded_pct}%</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── 탭 구성 ─────────────────────────────────────────────────
tab_map, tab_list, tab_stat, tab_ai = st.tabs(["🗺️ 지도", "📋 목록", "📊 통계", "💬 AI 추천"])

# ── 탭1: 지도 ───────────────────────────────────────────────
with tab_map:
    # 필터
    regions = ["전체"] + sorted(df_merged["ctpvNm"].dropna().unique().tolist())
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    sel_region = col_f1.selectbox("지역 필터", regions)
    sel_status = col_f2.multiselect("혼잡도 필터", ["여유", "보통", "혼잡"], default=["여유", "보통", "혼잡"])
    sel_oper = col_f3.multiselect("운영상태", ["운영중", "휴관"], default=["운영중"])

    df_filtered = df_merged.copy()
    if sel_region != "전체":
        df_filtered = df_filtered[df_filtered["ctpvNm"] == sel_region]
    df_filtered = df_filtered[df_filtered["status"].isin(sel_status)]
    if "operSttsNm" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["operSttsNm"].isin(sel_oper)]



    # 지도 생성
    center_lat = df_filtered["lat"].mean() if len(df_filtered) > 0 else 36.5
    center_lot = df_filtered["lot"].mean() if len(df_filtered) > 0 else 127.5
    m = folium.Map(
        location=[center_lat, center_lot],
        zoom_start=8 if sel_region != "전체" else 7,
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        min_zoom=6,
        max_bounds=True,
    )
    m.fit_bounds([[33.0, 124.5], [38.9, 132.0]])

    color_map = {"여유": "green", "보통": "orange", "혼잡": "red"}

    for _, row in df_filtered.iterrows():
        color = color_map.get(row["status"], "gray")
        open_str = fmt_time(row["wkdyOperBgngTm"])
        close_str = fmt_time(row["wkdyOperEndTm"])
        oper = row.get("operSttsNm", "정보없음")
        oper_color = "#1D9E75" if oper == "운영중" else "#888888"
        popup_html = f"""
        <div style='font-family:sans-serif; min-width:160px'>
          <b style='font-size:14px'>{row['pblibNm']}</b><br>
          <span style='background:{oper_color};color:white;padding:1px 6px;border-radius:4px;font-size:11px'>{oper}</span>
          <span style='color:{"#1D9E75" if row["status"]=="여유" else "#BA7517" if row["status"]=="보통" else "#E24B4A"}'>
            &nbsp;● {row['status']}</span><br>
          잔여석: <b>{int(row['rmnd_seats'])}</b> / {int(row['total_seats'])}석<br>
          운영: {open_str} ~ {close_str}<br>
          <small style='color:{get_freshness(row.get("latest_update"))[1]}'>{get_freshness(row.get("latest_update"))[0]}</small><br>
          <small>{row['pblibRoadNmAddr']}</small>
        </div>"""
        folium.CircleMarker(
            location=[row["lat"], row["lot"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{row['pblibNm']} ({row['status']}) | 잔여 {int(row['rmnd_seats'])}석"
        ).add_to(m)

    folium_static(m, width=1200, height=520)

    # 범례 (지도 아래)
    st.markdown(f"""
    <div style='display:flex;gap:24px;align-items:center;padding:8px 4px;font-size:13px;'>
      <span style='font-weight:600;color:#444'>혼잡도</span>
      <span style='display:flex;align-items:center;gap:6px'>
        <span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:#2ca25f'></span>
        <b>여유</b>
      </span>
      <span style='display:flex;align-items:center;gap:6px'>
        <span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:#fd8d3c'></span>
        <b>보통</b>
      </span>
      <span style='display:flex;align-items:center;gap:6px'>
        <span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:#e31a1c'></span>
        <b>혼잡</b>
      </span>
      <span style='color:#ddd;margin:0 4px'>|</span>
      <span style='color:#888'>마커 클릭 시 상세 정보 확인</span>
      <span style='margin-left:auto;color:#aaa;font-size:12px'>총 {len(df_filtered)}개 도서관 표시</span>
    </div>
    """, unsafe_allow_html=True)

# ── 탭2: 목록 ───────────────────────────────────────────────
with tab_list:
    # 검색창
    search_query = st.text_input("🔍 도서관 검색", placeholder="도서관 이름을 입력하세요 (예: 중앙도서관, 광진)")

    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
    sel_region2 = col_f1.selectbox("지역", ["전체"] + sorted(df_merged["ctpvNm"].dropna().unique().tolist()), key="r2")
    sel_status2 = col_f2.multiselect("혼잡도", ["여유", "보통", "혼잡"], default=["여유", "보통", "혼잡"], key="s2")
    sel_oper2 = col_f3.multiselect("운영상태", ["운영중", "휴관"], default=["운영중", "휴관"], key="o2")
    sort_by = col_f4.selectbox("정렬", ["잔여석 많은 순", "잔여석 적은 순", "혼잡도순"])

    df_list = df_merged.copy()
    if search_query:
        # 검색어 입력시 이름으로만 필터링 (다른 필터 무시)
        df_list = df_list[df_list["pblibNm"].str.contains(search_query, na=False)]
    else:
        # 검색어 없을 때만 필터 적용
        if sel_region2 != "전체":
            df_list = df_list[df_list["ctpvNm"] == sel_region2]
        df_list = df_list[df_list["status"].isin(sel_status2)]
        if "operSttsNm" in df_list.columns:
            df_list = df_list[df_list["operSttsNm"].isin(sel_oper2)]

    if sort_by == "잔여석 많은 순":
        df_list = df_list.sort_values("rmnd_seats", ascending=False)
    elif sort_by == "잔여석 적은 순":
        df_list = df_list.sort_values("rmnd_seats", ascending=True)
    else:
        order = {"혼잡": 0, "보통": 1, "여유": 2}
        df_list = df_list.sort_values("status", key=lambda x: x.map(order))

    # 목록 출력
    for _, row in df_list.iterrows():
        oper = row.get("operSttsNm", "정보없음")
        oper_icon = "🟢" if oper == "운영중" else "⚫"
        with st.expander(f"{'🟢' if row['status']=='여유' else '🟡' if row['status']=='보통' else '🔴'} "
                         f"{row['pblibNm']}  |  잔여 {int(row['rmnd_seats'])}석 / {int(row['total_seats'])}석  "
                         f"|  {row['ctpvNm']} {row['sggNm']}  |  {oper_icon} {oper}"):
            c1, c2 = st.columns(2)
            c1.write(f"**운영상태** {oper}")
            c1.write(f"**운영시간** {fmt_time(row['wkdyOperBgngTm'])} ~ {fmt_time(row['wkdyOperEndTm'])}")
            c1.write(f"**휴관일** {row['clsrInfoExpln']}")
            c1.write(f"**주소** {row['pblibRoadNmAddr']}")
            if pd.notna(row.get("pblibTelno")) and str(row.get("pblibTelno","")).strip():
                c1.write(f"**전화** {fmt_tel(str(row['pblibTelno']))}")
            # 홈페이지 바로가기
            site = str(row.get("siteUrlAddr", "")).strip()
            if site and site != "nan" and site.startswith("http"):
                c1.markdown(f'<a href="{site}" target="_blank">🔗 홈페이지 바로가기</a>', unsafe_allow_html=True)
            c2.write(f"**열람실 수** {int(row['room_count'])}개")
            c2.write(f"**사용 좌석** {int(row['used_seats'])}석")
            c2.write(f"**잔여 좌석** {int(row['rmnd_seats'])}석")
            if "tdyVstrCnt" in row and pd.notna(row["tdyVstrCnt"]):
                c2.write(f"**오늘 방문자** {int(row['tdyVstrCnt'])}명")
            try:
                lu = row["latest_update"]
                freshness_txt, freshness_color = get_freshness(lu)
                c2.markdown(f"<span style='font-size:12px;color:{freshness_color}'>● {freshness_txt}</span>", unsafe_allow_html=True)
            except:
                pass

            # 열람실 상세 (유형 필터 포함)
            df_rooms = get_room_detail(df_seat, row["pblibNm"])
            if len(df_rooms) > 0:
                st.dataframe(
                    df_rooms.rename(columns={
                        "rdrmNm": "열람실명", "rdrmTypeNm": "유형",
                        "bldgFlrExpln": "층", "tseatCnt": "총좌석",
                        "useSeatCnt": "사용", "rmndSeatCnt": "잔여"
                    }),
                    use_container_width=True, hide_index=True
                )

# ── 탭3: 통계 ───────────────────────────────────────────────
with tab_stat:
    import plotly.express as px

    st.subheader("📊 지역별 도서관 현황")

    # 지역별 집계
    df_stat = df_merged.groupby("ctpvNm").agg(
        도서관수=("pblibNm", "count"),
        평균잔여석=("rmnd_seats", "mean"),
        평균사용률=("ratio", "mean"),
        전체잔여석=("rmnd_seats", "sum"),
        전체좌석=("total_seats", "sum")
    ).reset_index()
    df_stat["평균사용률"] = (df_stat["평균사용률"] * 100).round(1)
    df_stat["평균잔여석"] = df_stat["평균잔여석"].round(0).astype(int)
    df_stat = df_stat.sort_values("평균사용률", ascending=True)

    # AI 리포트 생성 버튼
    st.markdown("**💬 AI 현황 리포트**")
    st.caption("현재 데이터를 기반으로 AI가 전국 도서관 현황을 요약해드려요")

    if st.button("✨ 지금 현황 리포트 생성", type="primary"):
        with st.spinner("AI가 분석 중..."):
            try:
                report_question = (
                    f"지금 전국 공공도서관 현황을 리포트 형식으로 요약해줘. "
                    f"전체 {len(df_merged)}개 도서관 기준으로 "
                    f"지역별 혼잡도 현황, 가장 여유로운 곳과 혼잡한 곳, "
                    f"지금 당장 가기 좋은 도서관 TOP 3를 포함해서 정리해줘. "
                    f"마크다운 헤더(#)는 사용하지 말고, 섹션 제목은 **볼드** 처리해줘. "
                    f"읽기 쉽고 자연스러운 문장으로 작성해줘."
                )
                report_history = [{"role": "user", "content": report_question}]
                report = ask_ai_chat(report_history, df_merged, df_seat)
                report_clean = "\n".join(
                    line.lstrip("#").strip() if line.startswith("#") else line
                    for line in report.split("\n")
                )
                st.markdown(report_clean)
            except Exception as e:
                st.error(f"리포트 생성 오류: {e}")

    # 요약 테이블
    st.markdown("**지역별 상세 현황**")
    df_display = df_stat[["ctpvNm", "도서관수", "전체잔여석", "전체좌석", "평균사용률"]].copy()
    df_display.columns = ["지역", "도서관 수", "잔여석", "전체좌석", "평균 사용률 (%)"]
    df_display = df_display.sort_values("평균 사용률 (%)", ascending=False)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("**지역별 평균 좌석 사용률 (%)**")
        fig1 = px.bar(
            df_stat, x="평균사용률", y="ctpvNm",
            orientation="h",
            color="평균사용률",
            color_continuous_scale=["#2ca25f", "#fd8d3c", "#e31a1c"],
            range_color=[0, 100],
            labels={"ctpvNm": "지역", "평균사용률": "사용률 (%)"},
            height=420
        )
        fig1.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white",
            yaxis_title="",
            xaxis_title="사용률 (%)"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_c2:
        st.markdown("**지역별 도서관 수**")
        df_stat2 = df_stat.sort_values("도서관수", ascending=True)
        fig2 = px.bar(
            df_stat2, x="도서관수", y="ctpvNm",
            orientation="h",
            color="도서관수",
            color_continuous_scale=["#B5D4F4", "#185FA5"],
            labels={"ctpvNm": "지역", "도서관수": "도서관 수"},
            height=420
        )
        fig2.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white",
            yaxis_title="",
            xaxis_title="도서관 수"
        )
        st.plotly_chart(fig2, use_container_width=True)


# ── 탭4: AI 추천 (대화형 채팅) ───────────────────────────────
with tab_ai:
    st.subheader("💬 AI 도서관 추천")
    st.caption("GPT-4o-mini 기반 · 실시간 잔여석 데이터를 참고해 추천해드려요 · 이어서 대화할 수 있어요")

    # 채팅 히스토리 초기화
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "안녕하세요! 저는 전국 공공도서관 실시간 잔여석 데이터를 보고 있는 AI예요 📚\n\n지역, 혼잡도, 운영시간 등 원하는 조건을 자유롭게 말씀해주세요!"
            }
        ]

    # 예시 질문 버튼
    ex_cols = st.columns(4)
    now_hour = datetime.now().hour
    examples = [
        "지금 당장 갈 수 있는 도서관 추천해줘",
        "혼자 조용히 공부하기 좋은 곳 어디야?",
        "그룹 스터디하기 좋은 넓은 도서관 추천해줘",
        "경기도 도서관 중 오늘 늦게까지 여는 곳은?"
    ]
    for i, ex in enumerate(examples):
        if ex_cols[i].button(ex, use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": ex})
            with st.spinner("AI가 분석 중..."):
                try:
                    answer = ask_ai_chat(st.session_state.chat_history, df_merged, df_seat)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"오류가 발생했어요: {e}"})
            st.rerun()

    # 채팅 메시지 출력
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="assistant" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # 채팅 입력창
    if prompt := st.chat_input("도서관에 대해 자유롭게 질문해보세요..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="assistant"):
            with st.spinner("분석 중..."):
                try:
                    answer = ask_ai_chat(st.session_state.chat_history, df_merged, df_seat)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    st.markdown(answer)
                except Exception as e:
                    err_msg = f"AI 오류가 발생했어요: {e}"
                    st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
                    st.error(err_msg)

    # 대화 초기화 버튼
    col_reset, _ = st.columns([1, 5])
    if col_reset.button("🔄 대화 초기화"):
        st.session_state.chat_history = [
            {"role": "assistant", "content": "안녕하세요! 저는 전국 공공도서관 실시간 잔여석 데이터를 보고 있는 AI예요 📚\n\n지역, 혼잡도, 운영시간 등 원하는 조건을 자유롭게 말씀해주세요!"}
        ]
        st.rerun()

    st.caption("※ AI 추천은 현재 시점의 잔여석 데이터를 기반으로 합니다. 실제 상황과 다를 수 있어요.")