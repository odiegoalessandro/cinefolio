import assert from 'node:assert/strict';
import test from 'node:test';

async function loadApiModule() {
  try {
    // Confirma que api.js pode ser importado de forma independente,
    // sem exigir um ambiente de navegador (window/document) — importante
    // porque este arquivo é testado com Node puro, não num navegador real
    return await import('../api.js');
  } catch (error) {
    assert.fail(`api.js must be importable without a browser: ${error.message}`);
  }
}

// Cria uma resposta HTTP "falsa" mínima, compatível com o que
// createApiClient espera receber de volta do fetch
function response({ ok = true, body = '' } = {}) {
  return {
    ok,
    async text() {
      return body;
    },
  };
}

test('get sends JSON headers and returns parsed data', async () => {
  const { createApiClient } = await loadApiModule();
  const calls = [];
  // Injeta um "fetch" falso que só registra a chamada recebida (para o
  // teste poder inspecionar depois) e devolve uma resposta simulada
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"results":[1]}' });
  });

  const result = await client.get('/api/movies/popular');

  assert.deepEqual(result, { results: [1] });
  // Confirma que o método GET foi chamado com os headers JSON padrão
  assert.deepEqual(calls, [
    {
      path: '/api/movies/popular',
      options: {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      },
    },
  ]);
});

test('post serializes its body as JSON', async () => {
  const { createApiClient } = await loadApiModule();
  const calls = [];
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"ok":true}' });
  });

  await client.post('/api/auth/login', { username: 'diego' });

  // Confirma que o objeto JS foi convertido em texto JSON antes de virar body
  assert.equal(calls[0].options.body, '{"username":"diego"}');
  assert.equal(calls[0].options.method, 'POST');
});

test('putForm sends FormData without a JSON content type', async () => {
  const { createApiClient } = await loadApiModule();
  const calls = [];
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"user":{"avatar_url":"/uploads/avatars/a.png"}}' });
  });
  const formData = new FormData();
  formData.set('avatar', new Blob(['image'], { type: 'image/png' }), 'a.png');

  await client.putForm('/api/profile/avatar', formData);

  assert.equal(calls[0].path, '/api/profile/avatar');
  assert.equal(calls[0].options.method, 'PUT');
  assert.equal(calls[0].options.headers.Accept, 'application/json');
  // Confirma explicitamente que NENHUM Content-Type foi setado à mão:
  // isso é essencial para o navegador poder gerar o boundary do
  // multipart corretamente sozinho
  assert.equal(calls[0].options.headers['Content-Type'], undefined);
  assert.equal(calls[0].options.body, formData);
});

test('API errors preserve the server message', async () => {
  const { createApiClient } = await loadApiModule();
  // ok: false simula uma resposta HTTP de erro (4xx/5xx)
  const client = createApiClient(async () =>
    response({ ok: false, body: '{"error":"Credenciais inválidas."}' })
  );

  // assert.rejects confirma que a Promise retornada é REJEITADA
  // (o client.post lança um Error), e que a mensagem bate com o regex
  await assert.rejects(
    client.post('/api/auth/login', {}),
    /Credenciais inválidas\./
  );
});

test('successful non-JSON responses become an empty object', async () => {
  const { createApiClient } = await loadApiModule();
  // Resposta "ok" mas com corpo que NÃO é JSON válido
  const client = createApiClient(async () => response({ body: 'plain text' }));

  // Confirma que isso não quebra o cliente: retorna objeto vazio em vez
  // de lançar um erro de parse
  assert.deepEqual(await client.get('/api/example'), {});
});
