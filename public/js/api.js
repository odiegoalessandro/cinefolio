// Headers padrão para requisições JSON: usados sempre que nenhum header
// customizado é especificado
const JSON_HEADERS = Object.freeze({
  'Content-Type': 'application/json',
  Accept: 'application/json',
});


// createApiClient cria um cliente HTTP configurável, injetando a
// implementação de fetch (por padrão, o fetch global do navegador) —
// isso permite testar o cliente com um "fetch falso" sem rede real
export function createApiClient(fetchImpl = globalThis.fetch) {
  async function request(path, options = {}) {
    // Desestrutura "headers" separadamente (com valor padrão JSON_HEADERS)
    // e junta o resto das opções (method, body etc) em requestOptions
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
      // Corpo vazio (ex: em alguns 204) não é JSON válido — trata como
      // objeto vazio em vez de deixar o JSON.parse() lançar erro
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      // Resposta não-JSON (ex: uma página de erro HTML): também vira
      // objeto vazio, para o restante do código sempre poder contar com
      // "data" sendo um objeto
      data = {};
    }

    if (!response.ok) {
      // Detecta um erro de configuração comum: o usuário abriu o frontend
      // servido por OUTRO servidor (ex: um Live Server do VS Code) que não
      // conhece as rotas /api/, e não pelo servidor Python do Cinefolio
      if (rawText.includes('Cannot GET') || rawText.includes('Cannot POST')) {
        throw new Error(
          'O frontend foi aberto no servidor errado. Use python -m server e abra http://127.0.0.1:8000.'
        );
      }

      // Usa a mensagem de erro que veio do backend (data.error), ou uma
      // mensagem genérica se por algum motivo ela não vier
      throw new Error(data.error || 'Não foi possível concluir a operação.');
    }

    return data;
  }

  // Object.freeze impede que o objeto retornado seja acidentalmente
  // modificado depois (ex: alguém sobrescrever client.get por engano)
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
      // Usado especificamente para o upload de avatar: quando o body é um
      // FormData (multipart), o Content-Type NÃO deve ser setado
      // manualmente — o navegador precisa gerar esse header sozinho,
      // incluindo o "boundary" correto automaticamente
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

// Instância pronta para uso direto no resto do app (usa o fetch real do navegador)
export const api = createApiClient();
