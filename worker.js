export default {
  async fetch(request) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors() });
    }

    const { searchParams } = new URL(request.url);
    const target = searchParams.get('url');

    if (!target) {
      return json({ error: 'url 파라미터 없음' }, 400);
    }

    // 한국 정부 도메인만 허용 (.go.kr)
    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return json({ error: '잘못된 URL' }, 400);
    }

    if (!targetUrl.hostname.endsWith('.go.kr')) {
      return json({ error: `허용되지 않은 도메인: ${targetUrl.hostname}` }, 403);
    }

    try {
      const res = await fetch(target, {
        method: 'GET',
        headers: { 'Accept': 'application/json, application/xml, */*' },
      });

      const body = await res.arrayBuffer();
      const ct = res.headers.get('Content-Type') || 'application/json';

      return new Response(body, {
        status: res.status,
        headers: { 'Content-Type': ct, ...cors() },
      });
    } catch (e) {
      return json({ error: '요청 실패', detail: e.message }, 502);
    }
  }
};

function cors() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors() },
  });
}
