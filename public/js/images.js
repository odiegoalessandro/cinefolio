const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500';
const EMPTY_MOVIE_IMAGE =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%231a1c24"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23737787" font-family="sans-serif" font-size="20"%3ESem Imagem%3C/text%3E%3C/svg%3E';

export function avatarImageUrl(url) {
  return (url || '').trim() || 'assets/default-avatar.svg';
}

export function bannerImageUrl(url) {
  return (url || '').trim() || 'assets/default-banner.svg';
}

export function movieImageUrl(path) {
  if (!path) {
    return EMPTY_MOVIE_IMAGE;
  }

  return /^https?:\/\//i.test(path)
    ? path
    : `${TMDB_IMAGE_BASE_URL}${path}`;
}
