# 🗳️ 2026 전국동시지방선거 개표현황 맵

KBS 방송용 실시간 지방선거 개표현황 지도 앱입니다.

## 📂 파일 구조

```
election-map/
├── index.html    ← 메인 앱 (이것만 GitHub Pages에 배포)
├── worker.js     ← Cloudflare Worker 프록시 (별도 배포)
└── README.md
```

---

## 🚀 GitHub Pages 배포

```bash
# 1. 저장소 생성 (예: election-map-2026)
git init
git add index.html README.md worker.js
git commit -m "초기 커밋"
git remote add origin https://github.com/[계정명]/election-map-2026.git
git push -u origin main

# 2. GitHub → Settings → Pages → Source: main branch → Save
# 3. 배포 URL: https://[계정명].github.io/election-map-2026/
```

---

## 🔑 API Key 보안 (중요!)

### ❌ 절대 하면 안 되는 것

```html
<!-- 이렇게 코드에 직접 넣으면 GitHub에 노출됩니다! -->
const API_KEY = 'AbCdEf1234567890...';
```

GitHub은 public 저장소면 전 세계에 공개됩니다. API Key가 코드에 있으면
봇들이 자동으로 스캔해서 악용됩니다.

---

### ✅ 이 앱의 보안 방식: **localStorage 저장**

이 앱은 API Key를 **코드에 넣지 않고**, 사용자가 브라우저에서 직접 입력하면
`localStorage`에만 저장됩니다.

```
[사용자 입력] → [브라우저 localStorage] → [API 호출 시 사용]
                       ↑
               GitHub 코드와 완전히 분리
               컴퓨터를 바꾸면 다시 입력 필요
```

**장점:**
- GitHub 저장소에 API Key가 절대 올라가지 않음
- `.gitignore` 설정 불필요
- 팀원이 각자 자신의 API Key 사용 가능

**단점:**
- 브라우저 개발자 도구(F12)에서 localStorage 확인 시 노출 가능
- → KBS 내부 PC에서만 사용하므로 실용적으로 문제없음

---

### 🛡️ 더 강력한 보안: 환경변수 + 빌드 방식

만약 GitHub Actions를 쓴다면:

```bash
# GitHub → Settings → Secrets and variables → Actions → New secret
# 이름: NEC_API_KEY
# 값: 실제 API 키
```

```yaml
# .github/workflows/build.yml
name: Build
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: 빌드 (API키 주입)
        run: |
          sed -i "s/PLACEHOLDER_KEY/${{ secrets.NEC_API_KEY }}/g" index.html
      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
```

> ⚠ 단, 이 방식은 최종 HTML에 키가 포함되므로 **프라이빗 저장소** 또는
> **내부망 배포** 시에만 권장합니다.

---

## 🌐 Cloudflare Worker 프록시 배포 (필수)

공공데이터포털 API(`apis.data.go.kr`)는 CORS 헤더가 없어서
**브라우저에서 직접 호출 불가**합니다. 중간에 프록시가 필요합니다.

### 배포 방법 (5분 소요, 무료)

**1단계**: https://workers.cloudflare.com 가입 (무료)

**2단계**: Dashboard → Workers & Pages → Create Application → Create Worker

**3단계**: `worker.js` 코드 전체를 에디터에 붙여넣기

**4단계**: "Save and Deploy" 클릭

**5단계**: 배포 URL 확인 (예: `https://election-proxy.your-name.workers.dev`)

**6단계**: 앱에서 ⚙ 설정 → "CORS 프록시 URL"에 위 URL 입력

### 프록시 작동 원리

```
[브라우저] → [Cloudflare Worker] → [apis.data.go.kr]
               (CORS 헤더 추가)         (선관위 API)
```

Worker는 `apis.data.go.kr` 도메인만 허용하도록 화이트리스트 처리되어 있습니다.

### 무료 사용 한도

Cloudflare Free Plan: **100,000 요청/일**
선거 당일 30초 폴링 × 17개 시도 = 분당 34회 = 시간당 2,040회
10시간 운영 시 최대 20,400회 → **무료 한도 내 충분**

---

## 🗺️ 사용법

### 선거 당일 운영 순서

1. `index.html` 열기
2. ⚙ **설정** 버튼 클릭
3. **실제 API 모드** 선택
4. **API Key** 입력 (자동 저장됨)
5. **프록시 URL** 입력
6. **저장 및 적용**
7. **▶ 실시간 시작** 클릭 → 30초마다 자동 갱신

### 지도 조작

| 동작 | 결과 |
|------|------|
| 시도 클릭 | 시군구 드릴다운 |
| "← 전국 지도" 클릭 | 전국 지도로 복귀 |
| 시도 마우스 오버 | 상세 툴팁 표시 |
| 우측 목록 클릭 | 해당 시도 드릴다운 |

---

## 🔧 선관위 API 명세 요약

**서비스명**: 투·개표 정보 조회 서비스 (VoteXmntckInfoInqireService2)
**개표결과 조회 엔드포인트**: `getXmntckSttusInfoInqire`

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| sgId | `20260603` | 제9회 전국동시지방선거 |
| sgTypecode | `3` | 시·도지사선거 |
| sdName | `서울특별시` 등 | 시도명 |
| numOfRows | `50` | 한 페이지 결과 수 |
| resultType | `json` | 응답 형식 |

**응답 필드:**
- `jd01`~`jd50`: 정당명
- `hbj01`~`hbj50`: 후보자명
- `dugsu01`~`dugsu50`: 득표수
- `yutusu`: 유효투표수
- `sunsu`: 선거인수

---

## 📋 기술 스택

- **지도**: D3.js v7 + southkorea-maps GeoJSON (시도/시군구)
- **API**: 중앙선거관리위원회 투·개표정보 OpenAPI
- **프록시**: Cloudflare Workers (무료)
- **배포**: GitHub Pages
- **프레임워크**: 없음 (순수 HTML/CSS/JS, 단일 파일)
