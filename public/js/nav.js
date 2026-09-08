import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { avatarImageUrl } from './images.js';
import { createPageUrl, navigateTo } from './navigation.js';

function createAuthenticatedNavigationMarkup(user, baseUrl) {
  const profileUrl = escapeHtml(
    createPageUrl('profile.html', { user: user.username }, baseUrl)
  );
  const avatarUrl = escapeHtml(avatarImageUrl(user.avatar_url));
  const displayName = escapeHtml(user.display_name);

  return `
    <ul class="navbar-nav ms-auto align-items-center gap-2">
      <li class="nav-item">
        <a class="nav-link d-flex align-items-center" href="${profileUrl}">
          <img class="user-nav-avatar" src="${avatarUrl}" alt="Avatar">
          <span>${displayName}</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="settings.html">Configurações</a>
      </li>
      <li class="nav-item">
        <button id="dynamic-logout-btn" class="btn btn-sm btn-outline-accent" type="button">Sair</button>
      </li>
    </ul>
  `;
}

export async function initializeNavigation({
  apiClient = api,
  documentRef = globalThis.document,
  locationRef = globalThis.location,
  alertFn = globalThis.alert,
} = {}) {
  const navAuthContainer = documentRef.querySelector('#nav-auth-container');
  const logoutButton = documentRef.querySelector('#logout-btn');

  const handleLogout = async (event) => {
    event?.preventDefault();

    try {
      await apiClient.post('/api/auth/logout', {});
      navigateTo('index.html', {}, locationRef);
    } catch (error) {
      alertFn(`Erro ao sair: ${error.message}`);
    }
  };

  logoutButton?.addEventListener('click', handleLogout);

  try {
    const { user } = await apiClient.get('/api/auth/me');
    if (!user) {
      return;
    }

    documentRef.querySelectorAll('.auth-link').forEach((link) => {
      link.href = createPageUrl(
        'profile.html',
        { user: user.username },
        locationRef.href
      );
      link.textContent = 'Meu Perfil';
    });

    documentRef
      .querySelector('#nav-settings-link')
      ?.classList.remove('d-none');
    documentRef
      .querySelector('#nav-register-link')
      ?.classList.add('d-none');
    logoutButton?.classList.remove('d-none');

    if (navAuthContainer) {
      navAuthContainer.innerHTML = createAuthenticatedNavigationMarkup(
        user,
        locationRef.href
      );
      documentRef
        .querySelector('#dynamic-logout-btn')
        ?.addEventListener('click', handleLogout);
    }
  } catch {
    // A ausência de sessão mantém a navegação pública.
  }
}
