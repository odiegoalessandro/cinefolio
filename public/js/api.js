const Api = {
  async request(path, options = {}) {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a operação.');
    return data;
  },
  get(path) { return this.request(path); },
  post(path, body) { return this.request(path, { method: 'POST', body: JSON.stringify(body) }); },
  put(path, body) { return this.request(path, { method: 'PUT', body: JSON.stringify(body) }); },
  delete(path) { return this.request(path, { method: 'DELETE' }); }
};
const imageUrl = path => path ? `https://image.tmdb.org/t/p/w500${path}` : 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%23263238"/%3E%3C/svg%3E';
