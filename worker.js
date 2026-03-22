/**
 * Cloudflare Worker - 선관위 API CORS 프록시
 * 파일명: worker.js
 *
 * 배포 방법:
 * 1. https://workers.cloudflare.com 접속 (무료 계정)
 * 2. "Create a Worker" 클릭
 * 3. 이 코드 전체 붙여넣기 → 저장 → 배포
 * 4. 배포된 URL (예: https://election-proxy.your-name.workers.dev) 을
 *    앱 설정의 "CORS 프록시 URL" 에 입력
 */

export default {
  async fetch(request, env) {
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const targetUrl = url.searchParams.get('url');

    if (!targetUrl) {
      return new Response(JSON.stringify({ error: 'url 파라미터 필요' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 보안: apis.data.go.kr 만 허용
    const allowed = ['apis.data.go.kr', 'sgisapi.kostat.go.kr', 'api.vworld.kr'];
    try {
      const targetHost = new URL(decodeURIComponent(targetUrl)).hostname;
      if (!allowed.includes(targetHost)) {
        return new Response(JSON.stringify({ error: '허용되지 않은 도메인' }), {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    } catch(e) {
      return new Response(JSON.stringify({ error: '잘못된 URL' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    try {
      const response = await fetch(decodeURIComponent(targetUrl), {
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      const text = await response.text();
      return new Response(text, {
        status: response.status,
        headers: {
          ...corsHeaders,
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
        },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
  },
};
