const App = {
  isFileProtocol: location.protocol === 'file:',
  page(name, params = {}) {
    const url = new URL(name, location.href);
    Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
    return url.href;
  },
  go(name, params) { location.href = this.page(name, params); },
  async request(path, options = {}) {
    if (this.isFileProtocol) throw new Error('Abra o Cinefolio pelo servidor: python3 -m server.main e depois http://127.0.0.1:8000.');
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
    const raw = await response.text();
    let data = {};
    try { data = raw ? JSON.parse(raw) : {}; } catch {}
    if (!response.ok) {
      if (raw.includes('Cannot GET') || raw.includes('Cannot POST')) {
        throw new Error('O frontend foi aberto no servidor errado. Pare o Live Server e use python3 -m server.main; depois abra http://127.0.0.1:8000.');
      }
      throw new Error(data.error || 'Não foi possível concluir a operação.');
    }
    return data;
  },
  get(path) { return this.request(path); },
  post(path, body) { return this.request(path, { method: 'POST', body: JSON.stringify(body) }); },
  put(path, body) { return this.request(path, { method: 'PUT', body: JSON.stringify(body) }); },
  delete(path) { return this.request(path, { method: 'DELETE' }); }
};

const Api = {
  get: path => App.get(path),
  post: (path, body) => App.post(path, body),
  put: (path, body) => App.put(path, body),
  delete: path => App.delete(path)
};

const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
const profileImageUrl = path => path?.trim() || 'assets/default-avatar.svg';
const bannerImageUrl = path => path?.trim() || 'assets/default-banner.svg';
const imageUrl = path => {
  if (!path) return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%23263238"/%3E%3C/svg%3E';
  return /^https?:\/\//i.test(path) ? path : `https://image.tmdb.org/t/p/w500${path}`;
};

document.addEventListener('DOMContentLoaded', () => {
  if (!App.isFileProtocol) return;
  document.body.innerHTML = '<main class="form-page"><section class="panel"><h1>Abra pelo servidor</h1><p>Esta aplicação precisa do backend Python para carregar dados, autenticação e páginas corretamente.</p><code>python3 -m server.main</code><p>Depois, acesse <strong>http://127.0.0.1:8000</strong> no navegador.</p></section></main>';
});
