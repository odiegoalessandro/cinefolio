/**
 * Cinefolio - Perfil Público e Visualização de Reviews
 */

document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const username = urlParams.get('user');

  const profileContainer = document.querySelector('#profile');
  const reviewDialog = document.querySelector('#review-dialog');
  const reviewTitle = document.querySelector('#review-title');
  const reviewRating = document.querySelector('#review-rating');
  const reviewContent = document.querySelector('#review-content');

  const sectionLabels = {
    favorites: '⭐ Favoritos',
    recently_watched: '🕒 Assistidos Recentemente',
    watching: '▶️ Assistindo Atualmente',
    watched: '✅ Todos os Assistidos',
    plan_to_watch: '📌 Pretende Assistir',
    dropped: '⏹️ Abandonados',
  };

  /**
   * Renderiza um card individual de filme dentro do perfil.
   * @param {object} movie - Dados do filme.
   * @returns {string} HTML do card.
   */
  function renderMovieCard(movie) {
    const title = escapeHtml(movie.title);
    const posterSrc = imageUrl(movie.poster_path);
    const movieUrl = App.page('movie.html', { id: movie.tmdb_id });

    const ratingHtml =
      movie.rating !== null && movie.rating !== undefined
        ? `<span class="poster-rating">★ ${escapeHtml(movie.rating)}</span>`
        : '<span class="text-muted small">Sem nota</span>';

    const favoriteBadge = movie.favorite
      ? '<span class="badge-favorite" title="Favorito">❤️</span>'
      : '';

    const hasReview = movie.review && movie.review.trim().length > 0;
    const reviewBtn = hasReview
      ? `
        <div class="poster-card-footer">
          <button class="btn btn-sm btn-outline-accent w-100 review-button"
                  type="button"
                  data-title="${title}"
                  data-rating="${movie.rating !== null ? escapeHtml(movie.rating) : ''}"
                  data-review="${escapeHtml(movie.review)}">
            Ler Review
          </button>
        </div>
      `
      : '';

    return `
      <article class="poster-card">
        <a class="poster-card-link" href="${movieUrl}">
          <div class="poster-image-wrap">
            <img src="${posterSrc}" alt="Pôster de ${title}" loading="lazy">
            ${favoriteBadge}
          </div>
          <div class="poster-card-body">
            <h3 class="poster-title" title="${title}">${title}</h3>
            <div class="poster-meta">
              ${ratingHtml}
            </div>
          </div>
        </a>
        ${reviewBtn}
      </article>
    `;
  }

  /**
   * Renderiza uma seção de filmes com grade ou estado vazio.
   * @param {Array} movies - Lista de filmes da seção.
   * @returns {string} HTML da grade.
   */
  function renderSectionGrid(movies) {
    if (!Array.isArray(movies) || movies.length === 0) {
      return '<div class="empty-state py-4"><p class="mb-0 text-muted">Nenhum filme catalogado nesta seção.</p></div>';
    }
    return `<div class="poster-grid">${movies.map(renderMovieCard).join('')}</div>`;
  }

  /**
   * Exibe mensagens no container principal de perfil.
   * @param {string} message - Texto informativo.
   */
  function showProfileMessage(message) {
    if (!profileContainer) return;
    profileContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">👤</div>
        <p class="mb-0">${escapeHtml(message)}</p>
      </div>
    `;
  }

  /**
   * Abre o diálogo modal com o review completo do filme.
   * @param {HTMLElement} button - Botão que acionou o modal com os datasets.
   */
  function openReviewDialog(button) {
    if (!reviewDialog) return;
    const title = button.dataset.title || 'Review do Filme';
    const rating = button.dataset.rating;
    const review = button.dataset.review || '';

    if (reviewTitle) reviewTitle.textContent = title;
    if (reviewRating) {
      reviewRating.textContent = rating ? `Avaliação: ★ ${rating} / 10` : 'Sem nota atribuída';
    }
    if (reviewContent) reviewContent.textContent = review;

    reviewDialog.showModal();
  }

  // ---------------------------------------------------------------------------
  // Eventos do Modal de Review
  // ---------------------------------------------------------------------------
  if (profileContainer) {
    profileContainer.addEventListener('click', (event) => {
      const button = event.target.closest('.review-button');
      if (button) {
        openReviewDialog(button);
      }
    });
  }

  document.querySelectorAll('.dialog-close-btn').forEach((btn) => {
    btn.addEventListener('click', () => reviewDialog?.close());
  });

  if (reviewDialog) {
    reviewDialog.addEventListener('click', (event) => {
      if (event.target === reviewDialog) {
        reviewDialog.close();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Carregamento dos Dados do Perfil
  // ---------------------------------------------------------------------------
  if (!username) {
    showProfileMessage('Informe um nome de usuário na URL para visualizar o perfil (ex.: profile.html?user=diego).');
    return;
  }

  showProfileMessage('Carregando dados do perfil...');

  Api.get(`/api/profiles/${encodeURIComponent(username)}`)
    .then(({ profile: data }) => {
      const displayName = escapeHtml(data.display_name);
      const userHandle = escapeHtml(data.username);
      const bio = escapeHtml(data.bio || 'Sem biografia informada.');
      const avatarSrc = profileImageUrl(data.avatar_url);
      const bannerSrc = bannerImageUrl(data.banner_url);

      const stats = data.stats || {};
      const watchedCount = escapeHtml(stats.watched_count ?? 0);
      const averageRating = stats.average_rating !== null && stats.average_rating !== undefined
        ? `★ ${escapeHtml(stats.average_rating)}`
        : '—';
      const reviewCount = escapeHtml(stats.review_count ?? 0);

      // Renderiza as seções de filmes
      const sectionsHtml = Object.entries(data.sections || {})
        .map(([key, movies]) => {
          const sectionLabel = sectionLabels[key] || escapeHtml(key);
          return `
            <section class="section mb-5">
              <div class="section-heading">
                <h2 class="section-title">${sectionLabel}</h2>
                <span class="badge bg-secondary rounded-pill">${movies.length}</span>
              </div>
              ${renderSectionGrid(movies)}
            </section>
          `;
        })
        .join('');

      profileContainer.innerHTML = `
        <header class="profile-banner" style="background-image: url('${bannerSrc}')">
          <div class="profile-header-content">
            <img class="profile-avatar" src="${avatarSrc}" alt="Avatar de ${displayName}">
            <div class="profile-info-wrap">
              <span class="hero-eyebrow">PERFIL PÚBLICO</span>
              <h1 class="profile-display-name">${displayName}</h1>
              <p class="profile-username">@${userHandle}</p>
              <p class="profile-bio">${bio}</p>
              <div class="profile-stats-bar">
                <div class="stat-item">
                  <span class="stat-value">${watchedCount}</span>
                  <span class="stat-label">Assistidos</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">${averageRating}</span>
                  <span class="stat-label">Média de Notas</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">${reviewCount}</span>
                  <span class="stat-label">Reviews</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main>
          ${sectionsHtml}
        </main>
      `;
    })
    .catch((error) => {
      showProfileMessage(error.message);
    });
});
