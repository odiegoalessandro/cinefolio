import { api } from './api.js';
import { initializeNavigation } from './nav.js';
import { navigateTo } from './navigation.js';

/**
 * Cinefolio - Configurações de Perfil e Gerenciamento de Conta
 */

function initializeSettingsPage() {
  const settingsForm = document.querySelector('#settings-form');
  const settingsMessage = document.querySelector('#settings-message');
  const deleteAccountBtn = document.querySelector('#delete-account-btn');

  /**
   * Exibe mensagens de feedback no painel de configurações.
   * @param {string} message - Texto da mensagem.
   * @param {boolean} isError - Define se a mensagem é de erro.
   */
  function showMessage(message, isError = false) {
    if (!settingsMessage) return;
    settingsMessage.textContent = message;
    settingsMessage.className = `alert ${isError ? 'alert-danger' : 'alert-success'} py-2 mt-3`;
    settingsMessage.classList.remove('d-none');
  }

  /**
   * Carrega os dados atuais do usuário autenticado no formulário.
   */
  async function loadUserSettings() {
    try {
      const { user } = await api.get('/api/auth/me');

      if (!user) {
        navigateTo('login.html');
        return;
      }

      // Preenche os campos do formulário
      if (settingsForm) {
        Object.entries(user).forEach(([key, value]) => {
          const input = settingsForm.querySelector(`[name="${key}"]`);
          if (input) {
            input.value = value || '';
          }
        });
      }
    } catch {
      navigateTo('login.html');
    }
  }

  // ---------------------------------------------------------------------------
  // Atualização do Perfil (Salvar Alterações)
  // ---------------------------------------------------------------------------
  if (settingsForm) {
    settingsForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const formData = new FormData(settingsForm);
      const payload = {
        display_name: (formData.get('display_name') || '').trim(),
        bio: (formData.get('bio') || '').trim(),
        avatar_url: (formData.get('avatar_url') || '').trim(),
        banner_url: (formData.get('banner_url') || '').trim(),
      };

      const submitBtn = settingsForm.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : 'Salvar Alterações';

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Salvando...';
        }

        await api.put('/api/profile', payload);
        showMessage('Perfil atualizado com sucesso!', false);
      } catch (error) {
        showMessage(error.message, true);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Exclusão Permanente da Conta
  // ---------------------------------------------------------------------------
  if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener('click', async () => {
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
  void initializeNavigation();
  initializeSettingsPage();
});
