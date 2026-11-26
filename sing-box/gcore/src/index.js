import { KvStore } from 'fastedge::kv';

addEventListener('fetch', (event) => event.respondWith(handle(event.request)));

async function handle(request) {
  const key = new URL(request.url).pathname.replace(/^\//, '');
  if (!key) return new Response('Not found', { status: 404 });
  const entry = await KvStore.open('CONFIGS').getEntry(key);
  if (entry === null) return new Response('Not found', { status: 404 });
  return new Response(await entry.text(), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
