import assert from 'node:assert/strict';
import test from 'node:test';

async function loadApiModule() {
  try {
    return await import('../api.js');
  } catch (error) {
    assert.fail(`api.js must be importable without a browser: ${error.message}`);
  }
}

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
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"results":[1]}' });
  });

  const result = await client.get('/api/movies/popular');

  assert.deepEqual(result, { results: [1] });
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
  assert.equal(calls[0].options.headers['Content-Type'], undefined);
  assert.equal(calls[0].options.body, formData);
});

test('API errors preserve the server message', async () => {
  const { createApiClient } = await loadApiModule();
  const client = createApiClient(async () =>
    response({ ok: false, body: '{"error":"Credenciais inválidas."}' })
  );

  await assert.rejects(
    client.post('/api/auth/login', {}),
    /Credenciais inválidas\./
  );
});

test('successful non-JSON responses become an empty object', async () => {
  const { createApiClient } = await loadApiModule();
  const client = createApiClient(async () => response({ body: 'plain text' }));

  assert.deepEqual(await client.get('/api/example'), {});
});
