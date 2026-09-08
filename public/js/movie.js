import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { movieImageUrl } from './images.js';
import { initializeNavigation } from './nav.js';

/**
 * Cinefolio - Detalhes do Filme e Gerenciamento de Status no Perfil
 */

function initializeMoviePage() {
  const urlParams = new URLSearchParams(window.location.search);
  const movieId = urlParams.get('id');

  const movieDetailContainer = document.querySelector('#movie-detail');
  const movieForm = document.querySelector('#movie-form');
  const movieMessage = document.querySelector('#movie-message');
  const removeMovieBtn = document.querySelector('#btn-remove-movie');

  /**
   * Exibe mensagens no formulário de avaliação do filme.
   * @param {string} message - Texto da mensagem.
   * @param {boolean} isError - Se verdadeiro, formata como alerta de perigo.
   */
  function showFormMessage(message, isError = false) {
    if (!movieMessage) return;
    movieMessage.textContent = message;
    movieMessage.className = `alert ${isError ? 'alert-danger' : 'alert-success'} py-2 mt-3`;
    movieMessage.classList.remove('d-none');
  }

  /**
   * Exibe mensagens no container principal de detalhes.
   * @param {string} message - Texto informativo.
   */
  function showDetailMessage(message) {
    if (!movieDetailContainer) return;
    movieDetailContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🎬</div>
        <p class="mb-0">${escapeHtml(message)}</p>
      </div>
    `;
  }

  /**
   * Carrega e renderiza os dados do filme a partir do backend.
   */
  async function loadMovieDetails() {
    if (!movieId || !/^\d+$/.test(movieId)) {
      showDetailMessage('Por favor, selecione um filme válido pela busca da página inicial.');
      if (movieForm) movieForm.classList.add('d-none');
      return;
    }

    showDetailMessage('Carregando informações do filme...');

    try {
      const { movie } = await api.get(`/api/movies/${movieId}`);

      // Renderiza o cabeçalho do filme
      const title = escapeHtml(movie.title);
      const originalTitle = movie.original_title ? escapeHtml(movie.original_title) : '';
      const year = escapeHtml(movie.release_year || 'Ano n/d');
      const overview = escapeHtml(movie.overview || 'Sinopse não disponível.');
      const posterSrc = movieImageUrl(movie.poster_path);
      const backdropSrc = movieImageUrl(movie.backdrop_path);

      const genresHtml = Array.isArray(movie.genres) && movie.genres.length > 0
        ? movie.genres.map((g) => `<span class="genre-tag">${escapeHtml(g.name)}</span>`).join('')
        : '';

      movieDetailContainer.innerHTML = `
        <article class="movie-hero-backdrop" style="background-image: url('${backdropSrc}')">
          <div class="movie-hero-content">
            <img class="movie-hero-poster" src="${posterSrc}" alt="Pôster de ${title}">
            <div class="movie-hero-info">
              <h1 class="movie-hero-title">${title}</h1>
              <div class="movie-hero-meta">
                <span><strong>Lançamento:</strong> ${year}</span>
                ${originalTitle ? `<span>• <em>${originalTitle}</em></span>` : ''}
              </div>
              ${genresHtml ? `<div class="movie-hero-genres mb-3">${genresHtml}</div>` : ''}
              <p class="movie-hero-overview">${overview}</p>
            </div>
          </div>
        </article>
      `;

      // Preenche os campos do formulário se o filme já estiver no perfil
      if (movie.user_status && movieForm) {
        const status = movie.user_status;
        if (movieForm.elements['status']) movieForm.elements['status'].value = status.status || 'WATCHING';
        if (movieForm.elements['rating']) movieForm.elements['rating'].value = status.rating !== null ? status.rating : '';
        if (movieForm.elements['watched_at']) movieForm.elements['watched_at'].value = status.watched_at || '';
        if (movieForm.elements['review']) movieForm.elements['review'].value = status.review || '';
        if (movieForm.elements['favorite']) movieForm.elements['favorite'].checked = Boolean(status.favorite);

        if (removeMovieBtn) {
          removeMovieBtn.classList.remove('d-none');
        }
      }
    } catch (error) {
      showDetailMessage(error.message);
      if (movieForm) movieForm.classList.add('d-none');
    }
  }

  // ---------------------------------------------------------------------------
  // Submissão do Formulário de Avaliação (Salvar no Perfil)
  // ---------------------------------------------------------------------------
  if (movieForm) {
    movieForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      if (!movieId || !/^\d+$/.test(movieId)) {
        showFormMessage('Identificador de filme inválido.', true);
        return;
      }

      const formData = new FormData(movieForm);
      const payload = {
        status: formData.get('status'),
        favorite: formData.get('favorite') === 'on',
        rating: formData.get('rating') ? Number(formData.get('rating')) : null,
        review: (formData.get('review') || '').trim() || null,
        watched_at: formData.get('watched_at') || null,
      };

      const submitBtn = movieForm.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : 'Salvar no Perfil';

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Salvando...';
        }

        const result = await api.put(`/api/movies/${movieId}/profile`, payload);
        showFormMessage(result.message || 'Filme salvo com sucesso no seu perfil!', false);

        if (removeMovieBtn) {
          removeMovieBtn.classList.remove('d-none');
        }
      } catch (error) {
        showFormMessage(error.message, true);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Remoção do Filme do Perfil (Delete)
  // ---------------------------------------------------------------------------
  if (removeMovieBtn) {
    removeMovieBtn.addEventListener('click', async () => {
      if (!confirm('Deseja realmente remover este filme do seu perfil?')) {
        return;
      }

      try {
        await api.delete(`/api/movies/${movieId}/profile`);
        showFormMessage('Filme removido do seu perfil com sucesso.', false);
        movieForm.reset();
        removeMovieBtn.classList.add('d-none');
      } catch (error) {
        showFormMessage(error.message, true);
      }
    });
  }

  loadMovieDetails();
}

document.addEventListener('DOMContentLoaded', () => {
  void initializeNavigation();
  initializeMoviePage();
});
