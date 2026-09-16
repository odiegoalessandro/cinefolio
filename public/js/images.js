export const DEFAULT_BANNER_IMAGE = 'assets/default-banner.svg';

// Base de URL usada pela TMDB para servir imagens de pôsteres/capas em
// tamanho "w500" (largura de 500px) — a API só devolve o CAMINHO da
// imagem (ex: "/abc123.jpg"), então essa base precisa ser concatenada na frente
const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500';


// Imagem "placeholder" embutida diretamente como SVG codificado em URL
// (data URI): evita depender de um arquivo de imagem externo só para
// mostrar "Sem Imagem" quando um filme não tem pôster
const EMPTY_MOVIE_IMAGE =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%231a1c24"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23737787" font-family="sans-serif" font-size="20"%3ESem Imagem%3C/text%3E%3C/svg%3E';

export function avatarImageUrl(url) {
  // Se a URL vier vazia (ou só espaços), usa uma imagem padrão local de avatar
  return (url || '').trim() || 'assets/default-avatar.svg';
}

export function bannerImageUrl(url) {
  // Mesma lógica do avatar, mas para o banner de capa do perfil
  return (url || '').trim() || DEFAULT_BANNER_IMAGE;
}

export function movieImageUrl(path) {
  if (!path) {
    return EMPTY_MOVIE_IMAGE;
  }


  // Se o caminho já é uma URL completa (começa com http:// ou https://),
  // usa ele direto; senão, assume que é um caminho relativo da TMDB e
  // completa com a base oficial de imagens
  return /^https?:\/\//i.test(path)
    ? path
    : `${TMDB_IMAGE_BASE_URL}${path}`;
}
