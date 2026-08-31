const id = new URLSearchParams(location.search).get('id');
const detail = document.querySelector('#movie-detail');

function showMovieMessage(message) { detail.innerHTML = `<p class="muted">${escapeHtml(message)}</p>`; }

async function loadMovie() {
  if (!id || !/^\d+$/.test(id)) return showMovieMessage('Escolha um filme pela busca para ver seus detalhes.');
  showMovieMessage('Carregando filme…');
  try {
    const { movie } = await Api.get(`/api/movies/${id}`);
    const genres = Array.isArray(movie.genres) ? movie.genres.map(genre => escapeHtml(genre.name)).join(' · ') : '';
    detail.innerHTML = `<div class="movie-hero" style="background-image:url('${imageUrl(movie.backdrop_path)}')"><div><img class="detail-poster" src="${imageUrl(movie.poster_path)}" alt="Poster de ${escapeHtml(movie.title)}"><section><h1>${escapeHtml(movie.title)}</h1><p>${escapeHtml(movie.release_year || '')}</p><p>${escapeHtml(movie.overview || 'Sinopse indisponível.')}</p><p>${genres}</p></section></div></div>`;
  } catch (error) { showMovieMessage(error.message); }
}

document.querySelector('#movie-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  if (!id || !/^\d+$/.test(id)) return document.querySelector('#movie-message').textContent = 'Escolha um filme pela busca antes de salvar.';
  const data = Object.fromEntries(new FormData(event.target));
  data.favorite = !!data.favorite;
  data.rating = data.rating === '' ? null : Number(data.rating);
  data.review = data.review || null;
  data.watched_at = data.watched_at || null;
  try { await Api.put(`/api/movies/${id}/profile`, data); document.querySelector('#movie-message').textContent = 'Filme salvo no perfil.'; }
  catch (error) { document.querySelector('#movie-message').textContent = error.message; }
});

loadMovie();
