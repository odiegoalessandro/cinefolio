const grid = document.querySelector('#movie-results');

function cards(movies) {
  grid.innerHTML = movies.map(movie => `<a class="poster-card" href="${App.page('movie.html', { id: movie.tmdb_id })}"><img src="${imageUrl(movie.poster_path)}" alt="Poster de ${escapeHtml(movie.title)}"><span>${escapeHtml(movie.title)}</span><small>${escapeHtml(movie.release_year || '')}</small></a>`).join('');
}

function showGridMessage(message) { grid.innerHTML = `<p class="muted">${escapeHtml(message)}</p>`; }

document.querySelector('#search-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  const query = event.target.q.value.trim();
  if (!query) return showGridMessage('Informe o nome de um filme para pesquisar.');
  showGridMessage('Buscando filmes…');
  try { cards((await Api.get(`/api/movies/search?q=${encodeURIComponent(query)}`)).results); }
  catch (error) { showGridMessage(error.message); }
});

showGridMessage('Carregando destaques…');
Api.get('/api/movies/popular').then(data => cards(data.results)).catch(error => showGridMessage(error.message));
