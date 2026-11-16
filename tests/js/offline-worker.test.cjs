const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

for (const online of [true, false]) {
  test(online ? 'script da fila usa versão da rede apesar do cache antigo' : 'script da fila continua disponível sem rede', async () => {
    const handlers = {};
    let cachedWrites = 0;
    const cache = { match: async () => new Response('antigo'), put: async () => { cachedWrites++; } };
    vm.runInNewContext(fs.readFileSync('app/static/sw.js', 'utf8'), {
      importScripts() {}, self: { location: { origin: 'https://example.test' },
        addEventListener: (name, handler) => { handlers[name] = handler; } },
      caches: { open: async () => cache }, Request, Response, URL,
      fetch: async (req) => {
        assert.equal(req.cache, 'no-store');
        if (!online) throw new Error('offline');
        return new Response('atual');
      }
    });
    let result;
    handlers.fetch({ request: new Request('https://example.test/static/js/offline-core.js?v=361916'),
      respondWith(promise) { result = promise; } });
    assert.equal(await (await result).text(), online ? 'atual' : 'antigo');
    assert.equal(cachedWrites, online ? 1 : 0);
  });
}
