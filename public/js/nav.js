import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { avatarImageUrl } from './images.js';
import { createPageUrl, navigateTo } from './navigation.js';


// Monta o HTML do menu de navegação para um usuário LOGADO (com foto,
// nome, link de configurações e botão de sair)
function createAuthenticatedNavigationMarkup(user, baseUrl) {
  // TUDO que vem do usuário (username, avatar_url, display_name) passa por
  // escapeHtml antes de entrar no template — proteção contra XSS
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

// initializeNavigation é chamada em TODA página do site (ver o final de
// cada arquivo .js de página) para configurar a barra de navegação
// compartilhada, adaptando-a conforme o usuário está logado ou não
export async function initializeNavigation({
  // Todos os parâmetros têm valor padrão (api real, document/location
  // globais, alert nativo) mas podem ser substituídos — o que facilita
  // MUITO testar esta função sem precisar de um navegador de verdade
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

  // O logoutButton "estático" (que já existe no HTML de cada página, para
  // quando o menu dinâmico ainda não carregou) recebe o handler direto
  logoutButton?.addEventListener('click', handleLogout);

  try {
    // Consulta se existe uma sessão ativa
    const { user } = await apiClient.get('/api/auth/me');
    if (!user) {
      return; // sem usuário: mantém a navegação padrão (pública)
    }

    // Atualiza todos os links marcados com a classe "auth-link" (ex: um
    // link genérico "Entrar" no topo) para apontarem para o perfil do
    // usuário logado, e trocam o texto para "Meu Perfil"
    documentRef.querySelectorAll('.auth-link').forEach((link) => {
      link.href = createPageUrl(
        'profile.html',
        { user: user.username },
        locationRef.href
      );
      link.textContent = 'Meu Perfil';
    });

    // Revela elementos que só fazem sentido para usuários logados, e
    // esconde os que só servem para visitantes (ex: link de "Cadastre-se")
    documentRef
      .querySelector('#nav-settings-link')
      ?.classList.remove('d-none');
    documentRef
      .querySelector('#nav-register-link')
      ?.classList.add('d-none');
    logoutButton?.classList.remove('d-none');

    // Substitui o container de autenticação pelo menu completo (com
    // avatar, nome e botão de sair "dinâmico")
    if (navAuthContainer) {
      navAuthContainer.innerHTML = createAuthenticatedNavigationMarkup(
        user,
        locationRef.href
      );
      // O botão de logout "dinâmico" (recém-criado via innerHTML) também
      // precisa ter seu próprio listener registrado, já que inseri-lo via
      // innerHTML não carrega os event listeners do botão estático
      documentRef
        .querySelector('#dynamic-logout-btn')
        ?.addEventListener('click', handleLogout);
    }
  } catch {
    // A ausência de sessão mantém a navegação pública.
    // (a chamada a /api/auth/me falha com 401 quando não há sessão —
    // isso é esperado e tratado silenciosamente aqui)
  }
}
