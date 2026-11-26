export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Remove leading slash: "/abc123/config.json" -> "abc123/config.json"
    const key = url.pathname.replace(/^\//, '');

    // Empty path -> 404
    if (!key) {
      return new Response('Not found', { status: 404 });
    }

    // Look up config in KV
    const config = await env.CONFIGS.get(key);

    if (config === null) {
      return new Response('Config not found', { status: 404 });
    }

    return new Response(config, {
      headers: {
        'Content-Type': 'application/json; charset=utf-8'
      }
    });
  }
};
