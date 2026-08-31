const grid = document.querySelector('#movie-results');
function cards(movies) { grid.innerHTML = movies.map(movie => `<a class="poster-card" href="/movie.html?id=${movie.tmdb_id}"><img src="${imageUrl(movie.poster_path)}" alt="Poster de ${movie.title}"><span>${movie.title}</span><small>${movie.release_year || ''}</small></a>`).join(''); }
document.querySelector('#search-form')?.addEventListener('submit', async e => { e.preventDefault(); try { cards((await Api.get(`/api/movies/search?q=${encodeURIComponent(e.target.q.value)}`)).results); } catch (error) { grid.innerHTML = `<p>${error.message}</p>`; } });
Api.get('/api/movies/popular').then(data => cards(data.results)).catch(() => { grid.innerHTML = '<p>Configure a TMDB para ver os destaques.</p>'; });
