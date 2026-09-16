import { api } from './api.js';
import { initializeAvatarSettings } from './avatar-settings.js';
import { initializeNavigation } from './nav.js';
import { navigateTo } from './navigation.js';

export function initializeSettingsPage() {
  const settingsForm = document.querySelector('#settings-form');
  const settingsMessage = document.querySelector('#settings-message');
  const deleteAccountBtn = document.querySelector('#delete-account-btn');
  // Agrupa todos os elementos do DOM ligados ao avatar, para passar de
  // uma vez só para initializeAvatarSettings via spread (...avatarControls)
  const avatarControls = {
    fileInput: document.querySelector('#input-avatar-file'),
    preview: document.querySelector('#avatar-preview'),
    removeButton: document.querySelector('#remove-avatar-btn'),
    uploadButton: document.querySelector('#upload-avatar-btn'),
  };
  let avatarSettings = null;

  function showMessage(message, isError = false) {
    if (!settingsMessage) return;
    settingsMessage.textContent = message;
    settingsMessage.className = `alert ${isError ? 'alert-danger' : 'alert-success'} py-2 mt-3`;
    settingsMessage.classList.remove('d-none');
  }

  async function loadUserSettings() {
    try {
      const { user } = await api.get('/api/auth/me');

      if (!user) {
        // Sem sessão ativa: expulsa o visitante para a tela de login,
        // já que a página de configurações exige estar logado
        navigateTo('login.html');
        return;
      }

      if (settingsForm) {
        // Preenche automaticamente cada campo do formulário cujo atributo
        // "name" corresponda a uma chave do objeto "user" (ex: input
        // name="display_name" recebe user.display_name)
        Object.entries(user).forEach(([key, value]) => {
          const input = settingsForm.querySelector(`[name="${key}"]`);
          if (input) {
            input.value = value || '';
          }
        });
      }

      // Só inicializa o módulo de avatar DEPOIS de saber a URL atual do
      // usuário (initialAvatarUrl), para a prévia começar correta
      avatarSettings = initializeAvatarSettings({
        apiClient: api,
        initialAvatarUrl: user.avatar_url,
        onMessage: showMessage,
        ...avatarControls,
      });
    } catch {
      // Falha ao buscar o usuário atual (ex: sessão expirada) também
      // redireciona para o login
      navigateTo('login.html');
    }
  }

  if (settingsForm) {
    settingsForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const formData = new FormData(settingsForm);
      // Monta o payload manualmente (em vez de enviar o FormData inteiro),
      // já que esta rota espera JSON e não multipart — e usa .trim() para
      // não salvar espaços em branco acidentais nas pontas
      const payload = {
        display_name: (formData.get('display_name') || '').trim(),
        bio: (formData.get('bio') || '').trim(),
        banner_url: (formData.get('banner_url') || '').trim(),
      };

      const submitBtn = settingsForm.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : 'Salvar Alterações';

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Salvando...';
        }

        const { user } = await api.put('/api/profile', payload);
        // Reaproveita o avatar_url retornado (mesmo que este formulário
        // não tenha alterado a foto) para manter a prévia sincronizada
        avatarSettings?.setAvatarUrl(user.avatar_url);
        showMessage('Perfil atualizado com sucesso!', false);
      } catch (error) {
        showMessage(error.message, true);
      } finally {
        // Aqui SEMPRE reabilita o botão (diferente do login), porque
        // atualizar o perfil não redireciona a página — o usuário
        // continua nela e pode querer salvar de novo
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }

  if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener('click', async () => {
      // confirm() é o diálogo nativo do navegador (OK/Cancelar) — usado
      // aqui como uma segunda confirmação para uma ação destrutiva e
      // irreversível (excluir a conta)
      const confirmed = confirm(
        'ATENÇÃO: Deseja realmente excluir sua conta permanentemente?\nTodos os seus filmes salvos, avaliações e sessões serão removidos e não poderão ser recuperados.'
      );

      if (!confirmed) return;

      try {
        await api.delete('/api/account');
        alert('Sua conta foi excluída com sucesso.');
        navigateTo('index.html');
      } catch (error) {
        showMessage('Erro ao excluir conta: ' + error.message, true);
      }
    });
  }

  loadUserSettings();
}

document.addEventListener('DOMContentLoaded', () => {
  // "void" descarta explicitamente a Promise retornada (deixa claro que
  // não estamos esquecendo um "await" por acidente, e sim ignorando
  // de propósito — a navegação pode terminar de carregar em segundo plano)
  void initializeNavigation();
  initializeSettingsPage();
});
