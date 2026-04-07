import requests
import pandas as pd
from datetime import datetime

API_KEY = "c9f4beae57129b828f00de75389a919585f8fd3aaf7f67604dac7c4f49522eb1"
BASE_URL = "https://apis.data.go.kr/B551982/plr_v2"


def fetch_library_info() -> pd.DataFrame:
    """도서관 기본정보 (위치, 운영시간 등)"""
    res = requests.get(f"{BASE_URL}/info_v2", params={
        "serviceKey": API_KEY,
        "type": "json",
        "numOfRows": 300,
        "pageNo": 1
    })
    items = res.json()["body"]["item"]
    df = pd.DataFrame(items)
    df = df.dropna(subset=["lat", "lot"])
    df["lat"] = df["lat"].astype(float)
    df["lot"] = df["lot"].astype(float)
    return df


def fetch_oper_status(df_info: pd.DataFrame) -> pd.DataFrame:
    """도서관 운영현황 (운영중/휴관, 방문자수, 좌석사용률 등)"""
    from datetime import datetime
    import time

    today = datetime.now().strftime("%Y%m%d")
    stdg_list = df_info["stdgCd"].unique().tolist()

    all_prst = []
    for cd in stdg_list:
        r = requests.get(f"{BASE_URL}/prst_info_v2", params={
            "serviceKey": API_KEY,
            "type": "json",
            "numOfRows": 50,
            "pageNo": 1,
            "stdgCd": cd,
            "fromCrtrYmd": today,
            "toCrtrYmd": today
        })
        try:
            items = r.json()["body"]["item"]
            if isinstance(items, list):
                all_prst.extend(items)
            elif isinstance(items, dict):
                all_prst.append(items)
        except:
            pass
        time.sleep(0.05)

    if not all_prst:
        return pd.DataFrame()

    df = pd.DataFrame(all_prst)
    df["tdyVstrCnt"] = pd.to_numeric(df["tdyVstrCnt"], errors="coerce").fillna(0).astype(int)
    df["tdyUseSeatCnt"] = pd.to_numeric(df["tdyUseSeatCnt"], errors="coerce").fillna(0).astype(int)
    df["seatUsgrt"] = pd.to_numeric(df["seatUsgrt"], errors="coerce").fillna(0)
    return df


def fetch_seat_info() -> pd.DataFrame:
    """열람실 실시간 잔여석 정보"""
    res = requests.get(f"{BASE_URL}/rlt_rdrm_info_v2", params={
        "serviceKey": API_KEY,
        "type": "json",
        "numOfRows": 500,
        "pageNo": 1
    })
    items = res.json()["body"]["item"]
    df = pd.DataFrame(items)

    for col in ["tseatCnt", "useSeatCnt", "rmndSeatCnt", "rsvtSeatCnt"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    def parse_totdt(val):
        try:
            return datetime.strptime(str(val), "%Y%m%d%H%M%S")
        except:
            return None

    df["updatedAt"] = df["totDt"].apply(parse_totdt)
    return df


def get_freshness(updated_at) -> tuple:
    """데이터 신선도 반환 (표시 텍스트, 색상)"""
    import pandas as pd
    try:
        if updated_at is None:
            return "업데이트 시각 불명", "#888888"
        if pd.isnull(updated_at):
            return "업데이트 시각 불명", "#888888"
        # pandas Timestamp -> python datetime 변환
        if hasattr(updated_at, 'to_pydatetime'):
            updated_at = updated_at.to_pydatetime()
        diff = datetime.now() - updated_at
        minutes = int(diff.total_seconds() / 60)
        if minutes < 0:
            return "방금 업데이트", "#1D9E75"
        elif minutes < 10:
            return f"{minutes}분 전 업데이트", "#1D9E75"
        elif minutes < 60:
            return f"{minutes}분 전 업데이트", "#BA7517"
        else:
            hours = minutes // 60
            return f"{hours}시간 전 업데이트", "#E24B4A"
    except:
        return "업데이트 시각 불명", "#888888"


def get_status(ratio: float) -> str:
    if ratio >= 0.8:
        return "혼잡"
    elif ratio >= 0.5:
        return "보통"
    else:
        return "여유"


def build_merged_df(df_info: pd.DataFrame, df_seat: pd.DataFrame, df_prst: pd.DataFrame = None) -> pd.DataFrame:
    """도서관 단위로 집계 후 위치 정보 + 운영현황 병합"""
    agg = df_seat.groupby("pblibNm").agg(
        total_seats=("tseatCnt", "sum"),
        used_seats=("useSeatCnt", "sum"),
        rmnd_seats=("rmndSeatCnt", "sum"),
        room_count=("rdrmNm", "count"),
        latest_update=("updatedAt", "max")
    ).reset_index()

    agg["ratio"] = agg["used_seats"] / agg["total_seats"].replace(0, 1)
    agg["status"] = agg["ratio"].apply(get_status)

    cols = ["pblibNm", "lat", "lot", "ctpvNm", "sggNm",
            "pblibRoadNmAddr", "wkdyOperBgngTm", "wkdyOperEndTm",
            "clsrInfoExpln", "pblibTelno", "siteUrlAddr"]
    df_pos = df_info[cols].drop_duplicates("pblibNm")

    merged = agg.merge(df_pos, on="pblibNm", how="left").dropna(subset=["lat", "lot"])

    # 운영현황 병합 (있을 때만)
    if df_prst is not None and len(df_prst) > 0:
        prst_cols = ["pblibNm", "operSttsNm", "tdyVstrCnt", "tdyUseSeatCnt",
                     "seatUsgrt", "rsvtPsbltyYn", "utztnPsbltyRdrmCnt"]
        prst_cols = [c for c in prst_cols if c in df_prst.columns]
        merged = merged.merge(
            df_prst[prst_cols].drop_duplicates("pblibNm"),
            on="pblibNm", how="left"
        )
        merged["operSttsNm"] = merged["operSttsNm"].fillna("정보없음")
    else:
        merged["operSttsNm"] = "정보없음"

    return merged


def fmt_time(t: str) -> str:
    t = str(t).zfill(6)
    return f"{t[:2]}:{t[2:4]}"


def fmt_tel(tel: str) -> str:
    """전화번호 포맷 변환 (0212345678 → 02-1234-5678)"""
    t = str(tel).strip().replace("-", "").replace(" ", "")
    if not t or t == "nan":
        return ""
    try:
        if t.startswith("02"):
            # 서울 (02) 지역번호
            if len(t) == 9:
                return f"{t[:2]}-{t[2:5]}-{t[5:]}"
            elif len(t) == 10:
                return f"{t[:2]}-{t[2:6]}-{t[6:]}"
        elif t.startswith("0"):
            # 3자리 지역번호 (031, 051 등)
            if len(t) == 10:
                return f"{t[:3]}-{t[3:6]}-{t[6:]}"
            elif len(t) == 11:
                return f"{t[:3]}-{t[3:7]}-{t[7:]}"
        return t
    except:
        return t


def get_room_detail(df_seat: pd.DataFrame, lib_name: str) -> pd.DataFrame:
    """특정 도서관의 열람실별 상세 현황"""
    df = df_seat[df_seat["pblibNm"] == lib_name].copy()
    df["혼잡도"] = df["ratio"] if "ratio" in df.columns else df.apply(
        lambda r: get_status(r["useSeatCnt"] / r["tseatCnt"]) if r["tseatCnt"] > 0 else "정보없음", axis=1
    )
    return df[["rdrmNm", "rdrmTypeNm", "bldgFlrExpln", "tseatCnt", "useSeatCnt", "rmndSeatCnt", "혼잡도"]]