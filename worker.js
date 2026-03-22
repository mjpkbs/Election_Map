/**
 * Cloudflare Worker — CORS 프록시
 * ─────────────────────────────────
 * 허용 도메인: 선관위, SGIS(구/신), VWorld
 *
 * 【Cloudflare 에디터 붙여넣기 방법】
 *   workers.cloudflare.com → 워커 선택 → Edit Code
 *   → 기존 코드 전부 지우고 이 파일 전체 붙여넣기 → Save and Deploy
 */

const ALLOWED = [
  'apis.data.go.kr',       // 선관위 공공데이터포털
  'sgisapi.mods.go.kr',    // SGIS 국가데이터처 (현행)
  'sgisapi.kostat.go.kr',  // SGIS 통계청 (구 도메인, 혹시 몰라 유지)
  'api.vworld.kr',         // VWorld
];

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

addEventListener('fetch', event => {
  event.respondWith(handle(event.request));
});

async function handle(request) {
  // CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS });
  }

  const { searchParams } = new URL(request.url);
  const raw = searchParams.get('url');

  if (!raw) {
    return json({ error: 'url 파라미터 필요' }, 400);
  }

  let decoded, host;
  try {
    decoded = decodeURIComponent(raw);
    host = new URL(decoded).hostname;
  } catch {
    return json({ error: '잘못된 URL 형식' }, 400);
  }

  if (!ALLOWED.includes(host)) {
    return json({ error: `허용되지 않은 도메인: ${host}` }, 403);
  }

  try {
    const res = await fetch(decoded, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; KBS-ElectionMap/1.0)',
        'Accept': 'application/json, application/geo+json, */*',
      },
      cf: { cacheTtl: 30 },  // Cloudflare 엣지 캐시 30초
    });

    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: {
        ...CORS,
        'Content-Type': res.headers.get('Content-Type') || 'application/json',
        'X-Proxy-Status': res.status.toString(),
      },
    });
  } catch (e) {
    return json({ error: e.message, host }, 502);
  }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}
