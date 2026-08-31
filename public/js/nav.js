/**
 * Cinefolio - Gerenciador da Barra de Navegação e Estado de Sessão
 */

document.addEventListener('DOMContentLoaded', () => {
  const navAuthContainer = document.querySelector('#nav-auth-container');
  const logoutBtn = document.querySelector('#logout-btn');

  // Manipulador de clique para encerrar a sessão
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async (event) => {
      event.preventDefault();
      try {
        await Api.post('/api/auth/logout', {});
        App.go('index.html');
      } catch (error) {
        alert('Erro ao sair: ' + error.message);
      }
    });
  }

  // Consulta se há um usuário autenticado na sessão ativa
  Api.get('/api/auth/me')
    .then(({ user }) => {
      if (!user) return;

      const authLinks = document.querySelectorAll('.auth-link');
      authLinks.forEach((link) => {
        link.href = App.page('profile.html', { user: user.username });
        link.textContent = 'Meu Perfil';
      });

      const navSettings = document.querySelector('#nav-settings-link');
      if (navSettings) {
        navSettings.classList.remove('d-none');
      }

      const navRegister = document.querySelector('#nav-register-link');
      if (navRegister) {
        navRegister.classList.add('d-none');
      }

      if (logoutBtn) {
        logoutBtn.classList.remove('d-none');
      }

      // Se houver um container dinâmico de navegação
      if (navAuthContainer) {
        const avatarSrc = profileImageUrl(user.avatar_url);
        navAuthContainer.innerHTML = `
          <ul class="navbar-nav ms-auto align-items-center gap-2">
            <li class="nav-item">
              <a class="nav-link d-flex align-items-center" href="${App.page('profile.html', { user: user.username })}">
                <img class="user-nav-avatar" src="${avatarSrc}" alt="Avatar">
                <span>${escapeHtml(user.display_name)}</span>
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

        document.querySelector('#dynamic-logout-btn')?.addEventListener('click', async () => {
          try {
            await Api.post('/api/auth/logout', {});
            App.go('index.html');
          } catch (error) {
            alert('Erro ao sair: ' + error.message);
          }
        });
      }
    })
    .catch(() => {
      // Usuário visitante não autenticado
    });
});
