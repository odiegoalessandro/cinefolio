/**
 * Cinefolio - Busca e Exibição de Filmes do Catálogo
 */

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('#movie-results');
  const searchForm = document.querySelector('#search-form');
  const sectionTitle = document.querySelector('#section-title');

  /**
   * Renderiza a lista de filmes em formato de cards responsivos.
   * @param {Array} movies - Lista de filmes.
   */
  function renderCards(movies) {
    if (!grid) return;

    if (!Array.isArray(movies) || movies.length === 0) {
      grid.innerHTML = `
        <div class="col-12 empty-state">
          <div class="empty-state-icon">🎬</div>
          <p class="mb-0">Nenhum filme encontrado para os critérios pesquisados.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = movies
      .map((movie) => {
        const title = escapeHtml(movie.title);
        const year = escapeHtml(movie.release_year || 'Ano n/d');
        const posterUrl = imageUrl(movie.poster_path);
        const moviePageUrl = App.page('movie.html', { id: movie.tmdb_id });

        return `
          <article class="poster-card">
            <a class="poster-card-link" href="${moviePageUrl}">
              <div class="poster-image-wrap">
                <img src="${posterUrl}" alt="Pôster de ${title}" loading="lazy">
              </div>
              <div class="poster-card-body">
                <h3 class="poster-title" title="${title}">${title}</h3>
                <div class="poster-meta">
                  <span>${year}</span>
                </div>
              </div>
            </a>
          </article>
        `;
      })
      .join('');
  }

  /**
   * Exibe o estado visual de carregamento.
   * @param {string} message - Texto informativo do spinner.
   */
  function showLoading(message = 'Buscando filmes...') {
    if (!grid) return;
    grid.innerHTML = `
      <div class="col-12 loading-spinner-wrap">
        <div class="spinner-custom"></div>
        <p class="mb-0">${escapeHtml(message)}</p>
      </div>
    `;
  }

  /**
   * Exibe mensagem de erro na grade.
   * @param {string} message - Mensagem de erro.
   */
  function showError(message) {
    if (!grid) return;
    grid.innerHTML = `
      <div class="col-12 empty-state text-danger">
        <div class="empty-state-icon">⚠️</div>
        <p class="mb-0">${escapeHtml(message)}</p>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Manipulação de Busca
  // ---------------------------------------------------------------------------
  if (searchForm) {
    searchForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const queryInput = searchForm.querySelector('input[name="q"]');
      const query = queryInput ? queryInput.value.trim() : '';

      if (!query) {
        showError('Por favor, informe o título de um filme para pesquisar.');
        return;
      }

      if (sectionTitle) {
        sectionTitle.textContent = `Resultados para "${query}"`;
      }

      showLoading('Consultando catálogo da TMDB...');

      try {
        const response = await Api.get(
          `/api/movies/search?q=${encodeURIComponent(query)}`
        );
        renderCards(response.results);
      } catch (error) {
        showError(error.message);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Carregamento Inicial de Filmes Populares
  // ---------------------------------------------------------------------------
  showLoading('Carregando destaques do catálogo...');
  Api.get('/api/movies/popular')
    .then((data) => {
      renderCards(data.results);
    })
    .catch((error) => {
      showError(error.message);
    });
});
