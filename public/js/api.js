const JSON_HEADERS = Object.freeze({
  'Content-Type': 'application/json',
  Accept: 'application/json',
});

export function createApiClient(fetchImpl = globalThis.fetch) {
  async function request(path, options = {}) {
    const { headers = JSON_HEADERS, ...requestOptions } = options;
    const response = await fetchImpl(path, {
      ...requestOptions,
      headers: {
        ...headers,
      },
    });
    const rawText = await response.text();

    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = {};
    }

    if (!response.ok) {
      if (rawText.includes('Cannot GET') || rawText.includes('Cannot POST')) {
        throw new Error(
          'O frontend foi aberto no servidor errado. Use python -m server e abra http://127.0.0.1:8000.'
        );
      }

      throw new Error(data.error || 'Não foi possível concluir a operação.');
    }

    return data;
  }

  return Object.freeze({
    get(path) {
      return request(path, { method: 'GET' });
    },
    post(path, body) {
      return request(path, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },
    put(path, body) {
      return request(path, {
        method: 'PUT',
        body: JSON.stringify(body),
      });
    },
    putForm(path, formData) {
      return request(path, {
        method: 'PUT',
        body: formData,
        headers: { Accept: 'application/json' },
      });
    },
    delete(path) {
      return request(path, { method: 'DELETE' });
    },
  });
}

export const api = createApiClient();
