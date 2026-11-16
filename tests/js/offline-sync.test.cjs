const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function fixture(response) {
  const context = { self: {}, FormData, URLSearchParams, URL, AbortController, setTimeout, clearTimeout,
    navigator: { onLine: true }, fetch: async (url, options) => {
      if (!options?.method) return { status: 200, ok: true, json: async () => ({ user_id: 1, csrf_token: 'fresh' }) };
      assert.equal(options.body.get('csrf_token'), 'fresh');
      assert.equal(options.headers['X-CSRF-Token'], 'fresh');
      assert.equal(options.headers['X-SP-Offline-Field-Count'], String(Array.from(options.body.keys()).filter(key => key !== 'csrf_token').length));
      return typeof response === 'function' ? response(url, options) : response;
    } };
  vm.runInNewContext(fs.readFileSync('app/static/js/offline-core.js', 'utf8'), context);
  const api = context.self.SafetyPlusOutbox;
  const item = { id: 'one', instance: 'one', user_id: 1, action: '/inspection/general/save',
    status: 'pending', entries: [['csrf_token', 'expired'], ['activity', 'Teste']] };
  let removed = false;
  api.list = async () => [item];
  api.getMap = async () => null;
  api.put = async () => {};
  api.remove = async () => { removed = true; };
  api.addHistory = async () => {};
  return { api, item, removed: () => removed };
}

test('erro de validação preserva registro e mostra motivo para revisão', async () => {
  const f = fixture({ ok: false, status: 422, url: 'https://example.test/inspection/general/save',
    text: async () => JSON.stringify({ detail: 'Campo obrigatório ausente' }) });
  const result = await f.api.flush();
  assert.equal(result.attention, 1);
  assert.equal(f.item.status, 'attention');
  assert.match(f.item.error, /Campo obrigatório ausente/);
  assert.equal(f.removed(), false);
  assert.equal(f.item.entries[1][1], 'Teste');
});

test('falha temporária mantém envio pendente para nova tentativa', async () => {
  const f = fixture({ ok: false, status: 503, url: 'https://example.test/inspection/general/save', text: async () => 'Unavailable' });
  const result = await f.api.flush();
  assert.equal(result.pending, 1);
  assert.equal(f.item.status, 'pending');
  assert.equal(f.removed(), false);
});

test('sucesso confirmado remove envio da fila', async () => {
  const f = fixture({ ok: true, status: 200, url: 'https://example.test/inspection/general/12/edit',
    text: async () => '<div class="flash flash-success">Salvo</div>' });
  f.api.setMap = async () => {};
  const result = await f.api.flush();
  assert.equal(result.sent, 1);
  assert.equal(f.removed(), true);
});

function csrfResponse() {
  return new Response(JSON.stringify({ detail: 'Sessão expirada ou token inválido. Atualize a página.' }), { status: 403 });
}

test('erro CSRF antigo volta a enviar automaticamente e renova token', async () => {
  let posts = 0;
  const f = fixture(() => {
    posts++;
    return posts === 1 ? csrfResponse() : { ok: true, status: 200,
      url: 'https://example.test/inspection/climber_assist/12/edit',
      text: async () => '<div class="flash flash-success">Salvo</div>' };
  });
  f.item.status = 'attention';
  f.item.error = 'O servidor recusou o envio (sessão ou permissão): Sessão expirada ou token inválido. Atualize a página.';
  f.api.setMap = async () => {};
  const result = await f.api.flush();
  assert.equal(posts, 2);
  assert.equal(result.sent, 1);
  assert.equal(f.removed(), true);
});

test('CSRF persistente mantém dados e pede novo login', async () => {
  const f = fixture(csrfResponse);
  f.item.entries.push(['offline_leader_password', 'preservada']);
  const result = await f.api.flush();
  assert.equal(result.pending, 1);
  assert.equal(result.attention, 0);
  assert.equal(f.item.status, 'pending');
  assert.match(result.error, /Faça login novamente/);
  assert.equal(f.item.entries.at(-1)[1], 'preservada');
  assert.equal(f.removed(), false);
});

test('recusa de permissão continua em revisão e não renova token', async () => {
  let posts = 0;
  const f = fixture(() => { posts++; return new Response(JSON.stringify({ detail: 'Acesso restrito' }), { status: 403 }); });
  const result = await f.api.flush();
  assert.equal(posts, 1);
  assert.equal(result.attention, 1);
  assert.equal(f.item.status, 'attention');
  assert.equal(f.removed(), false);
});


test('envio sem anexos usa formulário codificado e preserva campos repetidos e rubrica', async () => {
  const f = fixture((url, options) => {
    assert.ok(options.body instanceof URLSearchParams);
    assert.deepEqual(options.body.getAll('worker'), ['José', 'Ana']);
    assert.equal(options.body.get('signature'), 'data:image/png;base64,a+b/c==');
    return { ok: true, status: 200, url: 'https://example.test/inspection/general/12/edit', text: async () => '' };
  });
  f.item.entries.push(['worker', 'José'], ['worker', 'Ana'], ['signature', 'data:image/png;base64,a+b/c==']);
  f.api.setMap = async () => {};
  assert.equal((await f.api.flush()).sent, 1);
});

test('erro 400 antigo de formulário incompleto é recuperado sem recriar o registro', async () => {
  const f = fixture({ ok: true, status: 200, url: 'https://example.test/inspection/general/12/edit', text: async () => '' });
  f.item.status = 'attention';
  f.item.error = 'Servidor respondeu 400: O formulário chegou incompleto ao servidor. Os dados continuam no aparelho; tente enviar novamente.';
  f.api.setMap = async () => {};
  assert.equal((await f.api.flush()).sent, 1);
  assert.equal(f.removed(), true);
});

test('anexo real continua em multipart e não é convertido em texto', async () => {
  const f = fixture((url, options) => {
    assert.ok(options.body instanceof FormData);
    assert.equal(options.body.get('photo').name, 'foto.png');
    assert.equal(options.body.get('photo').size, 4);
    return { ok: false, status: 503, text: async () => '' };
  });
  f.item.entries.push(['photo', new File(['foto'], 'foto.png', { type: 'image/png' })]);
  await f.api.flush();
  assert.equal(f.removed(), false);
});

test('campo de arquivo vazio usa codificação simples sem perder contagem', async () => {
  const f = fixture((url, options) => {
    assert.ok(options.body instanceof URLSearchParams);
    assert.equal(options.body.get('photo'), '');
    return { ok: false, status: 503, text: async () => '' };
  });
  f.item.entries.push(['photo', new File([], '')]);
  await f.api.flush();
  assert.equal(f.removed(), false);
});
