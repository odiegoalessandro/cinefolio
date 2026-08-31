const username = new URLSearchParams(location.search).get('user');
const profile = document.querySelector('#profile');
const reviewDialog = document.querySelector('#review-dialog');
const reviewTitle = document.querySelector('#review-title');
const reviewRating = document.querySelector('#review-rating');
const reviewContent = document.querySelector('#review-content');
const labels = { favorites: 'Favoritos', recently_watched: 'Assistidos recentemente', watching: 'Assistindo', watched: 'Assistidos', plan_to_watch: 'Pretende assistir', dropped: 'Abandonados' };

function movieCard(movie) {
  const rating = movie.rating === null || movie.rating === undefined ? '' : `<small class="movie-rating">Nota: ${escapeHtml(movie.rating)}</small>`;
  const review = movie.review?.trim() ? `<button class="review-button" type="button" data-title="${escapeHtml(movie.title)}" data-rating="${escapeHtml(movie.rating ?? '')}" data-review="${escapeHtml(movie.review)}">Ler review</button>` : '';
  return `<article class="poster-card"><a href="${App.page('movie.html', { id: movie.tmdb_id })}"><img src="${imageUrl(movie.poster_path)}" alt="Poster de ${escapeHtml(movie.title)}"><span>${escapeHtml(movie.title)}</span></a>${rating}${review}</article>`;
}

function list(movies) {
  if (!Array.isArray(movies) || !movies.length) return '<p class="muted">Nenhum filme nesta seção.</p>';
  return `<div class="poster-grid">${movies.map(movieCard).join('')}</div>`;
}

function showProfileMessage(message) { profile.innerHTML = `<p class="muted">${escapeHtml(message)}</p>`; }

function showReview(button) {
  reviewTitle.textContent = button.dataset.title;
  reviewRating.textContent = button.dataset.rating ? `Nota: ${button.dataset.rating}` : 'Sem nota';
  reviewContent.textContent = button.dataset.review;
  reviewDialog.showModal();
}

profile.addEventListener('click', event => {
  const button = event.target.closest('.review-button');
  if (button) showReview(button);
});

document.querySelector('.dialog-close').addEventListener('click', () => reviewDialog.close());
reviewDialog.addEventListener('click', event => { if (event.target === reviewDialog) reviewDialog.close(); });

if (!username) {
  showProfileMessage('Informe o usuário do perfil na URL.');
} else {
  showProfileMessage('Carregando perfil público…');
  Api.get(`/api/profiles/${encodeURIComponent(username)}`).then(({ profile: data }) => {
    const sections = Object.entries(data.sections || {}).map(([key, movies]) => `<section class="section"><h2>${labels[key] || escapeHtml(key)}</h2>${list(movies)}</section>`).join('');
    profile.innerHTML = `<header class="profile-header" style="background-image:url('${bannerImageUrl(data.banner_url)}')"><div class="profile-info"><img class="avatar" src="${profileImageUrl(data.avatar_url)}" alt="Avatar de ${escapeHtml(data.display_name)}"><div><p class="eyebrow">PERFIL PÚBLICO</p><h1>${escapeHtml(data.display_name)}</h1><p>@${escapeHtml(data.username)}</p><p>${escapeHtml(data.bio)}</p><div class="stats"><span>${escapeHtml(data.stats?.watched_count || 0)} assistidos</span><span>${escapeHtml(data.stats?.average_rating || '—')} média</span><span>${escapeHtml(data.stats?.review_count || 0)} reviews</span></div></div></div></header>${sections}`;
  }).catch(error => showProfileMessage(error.message));
}
