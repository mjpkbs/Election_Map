export default {
  async fetch(request, env, ctx) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    const incoming = new URL(request.url);
    const target = incoming.searchParams.get('url');

    if (!target) {
      return new Response(JSON.stringify({ error: 'url 파라미터가 없습니다' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }

    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return new Response(JSON.stringify({ error: '유효하지 않은 URL입니다' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }

    // 허용 도메인 화이트리스트
    const ALLOWED = [
      'sgisapi.mods.go.kr',
      'apis.data.go.kr',
    ];
    if (!ALLOWED.some(d => targetUrl.hostname === d || targetUrl.hostname.endsWith('.' + d))) {
      return new Response(JSON.stringify({ error: '허용되지 않은 도메인입니다: ' + targetUrl.hostname }), {
        status: 403,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }

    try {
      const upstream = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; ElectionMapProxy/1.0)',
          'Accept': 'application/json, */*',
        },
        // GET/HEAD 외에는 body 전달
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      });

      const body = await upstream.arrayBuffer();
      const contentType = upstream.headers.get('Content-Type') || 'application/json';

      return new Response(body, {
        status: upstream.status,
        headers: {
          'Content-Type': contentType,
          ...corsHeaders(),
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: '업스트림 요청 실패', detail: err.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }
  },
};

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  };
}
