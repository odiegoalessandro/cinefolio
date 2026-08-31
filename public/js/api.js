/**
 * Cinefolio - Camada de Comunicação com a API e Utilitários Globais
 */

const App = {
  /**
   * Verifica se o arquivo foi aberto via protocolo file:// em vez do servidor HTTP.
   */
  isFileProtocol: window.location.protocol === 'file:',

  /**
   * Constrói uma URL com parâmetros de busca (query string).
   * @param {string} pageName - Nome da página (ex.: 'profile.html').
   * @param {Record<string, string>} params - Objeto com parâmetros chave/valor.
   * @returns {string} URL completa.
   */
  page(pageName, params = {}) {
    const url = new URL(pageName, window.location.href);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
    return url.href;
  },

  /**
   * Redireciona a navegação para uma página específica com parâmetros.
   * @param {string} pageName - Nome da página de destino.
   * @param {Record<string, string>} params - Parâmetros da URL.
   */
  go(pageName, params) {
    window.location.href = this.page(pageName, params);
  },

  /**
   * Executa requisições HTTP para a API local com tratamento de erros.
   * @param {string} path - Caminho do endpoint (ex.: '/api/auth/me').
   * @param {RequestInit} options - Opções da requisição Fetch.
   * @returns {Promise<any>}
   */
  async request(path, options = {}) {
    if (this.isFileProtocol) {
      throw new Error(
        'Abra o Cinefolio pelo servidor Python: python -m server.main e acesse http://127.0.0.1:8000.'
      );
    }

    const defaultHeaders = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    };

    const response = await fetch(path, config);
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
          'O frontend foi aberto no servidor errado. Use python -m server.main e abra http://127.0.0.1:8000.'
        );
      }
      throw new Error(data.error || 'Não foi possível concluir a operação.');
    }

    return data;
  },

  get(path) {
    return this.request(path, { method: 'GET' });
  },

  post(path, body) {
    return this.request(path, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  put(path, body) {
    return this.request(path, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  delete(path) {
    return this.request(path, { method: 'DELETE' });
  },
};

/**
 * Atalho semântico para chamadas de API.
 */
const Api = {
  get: (path) => App.get(path),
  post: (path, body) => App.post(path, body),
  put: (path, body) => App.put(path, body),
  delete: (path) => App.delete(path),
};

/**
 * Escapa caracteres HTML para prevenir ataques XSS.
 * @param {string|number|null} value - Texto a ser escapado.
 * @returns {string} Texto seguro.
 */
function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return String(value).replace(/[&<>'"]/g, (char) => map[char]);
}

/**
 * Retorna a URL segura da imagem do avatar ou imagem padrão local.
 * @param {string} url - URL informada pelo usuário.
 * @returns {string}
 */
function profileImageUrl(url) {
  const trimmed = (url || '').trim();
  return trimmed || 'assets/default-avatar.svg';
}

/**
 * Retorna a URL segura do banner do perfil ou imagem padrão local.
 * @param {string} url - URL informada pelo usuário.
 * @returns {string}
 */
function bannerImageUrl(url) {
  const trimmed = (url || '').trim();
  return trimmed || 'assets/default-banner.svg';
}

/**
 * Retorna a URL completa da imagem de pôster ou backdrop da TMDB.
 * @param {string} path - Caminho relativo da TMDB ou URL completa.
 * @returns {string}
 */
function imageUrl(path) {
  if (!path) {
    return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%231a1c24"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23737787" font-family="sans-serif" font-size="20"%3ESem Imagem%3C/text%3E%3C/svg%3E';
  }
  return /^https?:\/\//i.test(path) ? path : `https://image.tmdb.org/t/p/w500${path}`;
}

/**
 * Exibe um alerta de aviso caso a página tenha sido aberta via file://
 */
document.addEventListener('DOMContentLoaded', () => {
  if (!App.isFileProtocol) return;
  document.body.innerHTML = `
    <main class="form-center-page">
      <div class="panel-card text-center">
        <h1 class="panel-title text-danger">Atenção</h1>
        <p class="panel-subtitle">Esta aplicação precisa do backend Python para funcionar.</p>
        <div class="alert alert-warning text-start">
          <p class="mb-2"><strong>Como iniciar:</strong></p>
          <code>python -m server.main</code>
          <p class="mt-2 mb-0">Depois acesse no navegador: <strong>http://127.0.0.1:8000</strong></p>
        </div>
      </div>
    </main>
  `;
});
