"""
SGIS 통계지리정보서비스 → GeoJSON 다운로더
============================================
실행 전 준비:
  1. https://sgis.mods.go.kr/developer 에서 회원가입 → API 키 발급
     (CONSUMER_KEY, CONSUMER_SECRET 2개 발급됨)
  2. pip install requests

실행:
  python download_geo.py --key YOUR_CONSUMER_KEY --secret YOUR_CONSUMER_SECRET

결과:
  geo/sido.json      ← 시도(17개) GeoJSON  → index.html에서 로드
  geo/sigungu.json   ← 시군구(250개) GeoJSON → index.html에서 로드
"""

import argparse
import json
import math
import os
import sys
import requests

# ── SGIS API ────────────────────────────────────────────
AUTH_URL     = "https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json"
BOUNDARY_URL = "https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson"
YEAR         = "2023"   # 최신 행정구역 기준년도

# ── UTM-K (EPSG:5179) → WGS84 (EPSG:4326) 변환 ─────────
# SGIS API는 UTM-K 좌표로 반환 → D3.js용 WGS84로 변환 필요

# Transverse Mercator 파라미터 (GRS80 기반 UTM-K)
TM_A  = 6378137.0          # 장반경
TM_E2 = 0.00669438002290   # 이심률²
TM_K0 = 1.0                # 축척계수
TM_DX = 1000000.0          # X 원점 이동
TM_DY = 2000000.0          # Y 원점 이동
TM_LO = math.radians(127.5) # 중앙경선
TM_PO = math.radians(38.0)  # 원점위도

def utm_k_to_wgs84(x, y):
    """UTM-K 좌표 (x=Easting, y=Northing) → WGS84 (lon, lat)"""
    # 역 Transverse Mercator (Helmert 근사)
    x = x - TM_DX
    y = y - TM_DY

    e2  = TM_E2
    e4  = e2 * e2
    e6  = e4 * e2
    e1  = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))

    M0 = TM_A * ((1 - e2/4 - 3*e4/64 - 5*e6/256) * TM_PO
                 - (3*e2/8 + 3*e4/32 + 45*e6/1024) * math.sin(2*TM_PO)
                 + (15*e4/256 + 45*e6/1024) * math.sin(4*TM_PO)
                 - (35*e6/3072) * math.sin(6*TM_PO))

    M   = M0 + y / TM_K0
    mu  = M / (TM_A * (1 - e2/4 - 3*e4/64 - 5*e6/256))

    p1  = (3*e1/2 - 27*e1**3/32) * math.sin(2*mu)
    p2  = (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu)
    p3  = (151*e1**3/96) * math.sin(6*mu)
    p4  = (1097*e1**4/512) * math.sin(8*mu)
    phi = mu + p1 + p2 + p3 + p4

    sp  = math.sin(phi)
    cp  = math.cos(phi)
    tp  = sp / cp
    N   = TM_A / math.sqrt(1 - e2 * sp**2)
    T   = tp**2
    C   = e2 / (1-e2) * cp**2
    R   = TM_A * (1-e2) / (1 - e2*sp**2)**1.5
    D   = x / (N * TM_K0)

    lat = phi - (N*tp/R) * (D**2/2
          - (5+3*T+10*C-4*C**2-9*e2/(1-e2))*D**4/24
          + (61+90*T+298*C+45*T**2-252*e2/(1-e2)-3*C**2)*D**6/720)
    lon = TM_LO + (D
          - (1+2*T+C)*D**3/6
          + (5-2*C+28*T-3*C**2+8*e2/(1-e2)+24*T**2)*D**5/120) / cp

    return math.degrees(lon), math.degrees(lat)


def convert_coords(coords):
    """재귀적으로 좌표 배열 변환"""
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return list(utm_k_to_wgs84(coords[0], coords[1]))
    return [convert_coords(c) for c in coords]


def convert_feature(feature):
    """Feature 하나의 geometry 좌표 변환"""
    geom = feature.get("geometry", {})
    if not geom:
        return feature
    feature["geometry"]["coordinates"] = convert_coords(geom["coordinates"])
    return feature


# ── API 함수 ─────────────────────────────────────────────
def get_token(consumer_key, consumer_secret):
    r = requests.get(AUTH_URL, params={
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    token = data.get("result", {}).get("accessToken")
    if not token:
        raise RuntimeError(f"토큰 발급 실패: {data}")
    print(f"[OK] 토큰 발급 완료: {token[:20]}...")
    return token


def fetch_boundary(token, adm_cd="", low_search="1"):
    """
    adm_cd: 시도코드("") 전국 시도 / 시도코드(예:"11") 해당 시도의 시군구
    low_search: 1=시도, 2=시군구
    """
    r = requests.get(BOUNDARY_URL, params={
        "accessToken": token,
        "year": YEAR,
        "adm_cd": adm_cd,
        "low_search": low_search,
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("errCd", -1) != 0:
        raise RuntimeError(f"API 오류: {data.get('errMsg')} (adm_cd={adm_cd})")
    return data.get("result", {}).get("features", [])


# ── 메인 ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SGIS GeoJSON 다운로더")
    parser.add_argument("--key",    required=True, help="SGIS CONSUMER_KEY")
    parser.add_argument("--secret", required=True, help="SGIS CONSUMER_SECRET")
    args = parser.parse_args()

    os.makedirs("geo", exist_ok=True)
    token = get_token(args.key, args.secret)

    # ── 1) 시도 (17개) ────────────────────────────────────
    print("[1/2] 시도 경계 다운로드 중...")
    sido_features_raw = fetch_boundary(token, adm_cd="", low_search="1")

    # 좌표계 감지: x 값이 900000 이상이면 UTM-K
    sample_coord = None
    try:
        sample_coord = sido_features_raw[0]["geometry"]["coordinates"][0][0]
    except Exception:
        pass

    need_convert = sample_coord and abs(sample_coord[0]) > 500
    if need_convert:
        print("  → UTM-K 좌표 감지, WGS84로 변환 중...")

    sido_features = []
    for f in sido_features_raw:
        props = f.get("properties", {})
        # 속성 정규화
        name = props.get("adm_nm") or props.get("sidonm") or props.get("ctprvn_cd_nm") or ""
        code = props.get("adm_cd") or props.get("sido_cd") or props.get("ctprvn_cd") or ""
        feature = {
            "type": "Feature",
            "properties": {"name": name, "code": str(code)},
            "geometry": f.get("geometry", {}),
        }
        if need_convert:
            feature = convert_feature(feature)
        sido_features.append(feature)

    sido_geojson = {"type": "FeatureCollection", "features": sido_features}
    sido_path = "geo/sido.json"
    with open(sido_path, "w", encoding="utf-8") as fp:
        json.dump(sido_geojson, fp, ensure_ascii=False)
    print(f"  → 저장: {sido_path} ({len(sido_features)}개 시도)")

    # ── 2) 시군구 (전국, 시도별 순회) ────────────────────
    print("[2/2] 시군구 경계 다운로드 중 (시도별 순회)...")
    sigungu_features = []

    for f in sido_features:
        sido_code = f["properties"]["code"]
        sido_name = f["properties"]["name"]
        if not sido_code:
            continue
        try:
            sgg_raw = fetch_boundary(token, adm_cd=sido_code, low_search="2")
            for sf in sgg_raw:
                props = sf.get("properties", {})
                name = props.get("adm_nm") or props.get("sggnm") or props.get("sgg_nm") or ""
                code = props.get("adm_cd") or props.get("sgg_cd") or ""
                # 시도명 제거 (예: "서울특별시 종로구" → "종로구")
                if name.startswith(sido_name):
                    name = name[len(sido_name):].strip()
                feature = {
                    "type": "Feature",
                    "properties": {"name": name, "code": str(code), "sido": sido_code},
                    "geometry": sf.get("geometry", {}),
                }
                if need_convert:
                    feature = convert_feature(feature)
                sigungu_features.append(feature)
            print(f"  [{sido_code}] {sido_name}: {len(sgg_raw)}개 시군구")
        except Exception as e:
            print(f"  [경고] {sido_name}({sido_code}) 시군구 오류: {e}")

    sigungu_geojson = {"type": "FeatureCollection", "features": sigungu_features}
    sigungu_path = "geo/sigungu.json"
    with open(sigungu_path, "w", encoding="utf-8") as fp:
        json.dump(sigungu_geojson, fp, ensure_ascii=False)
    print(f"  → 저장: {sigungu_path} ({len(sigungu_features)}개 시군구)")

    print("\n✅ 완료! geo/ 폴더의 두 파일을 index.html과 같은 GitHub 레포에 커밋하세요.")
    print("   git add geo/sido.json geo/sigungu.json && git commit -m 'SGIS GeoJSON 추가'")


if __name__ == "__main__":
    main()
