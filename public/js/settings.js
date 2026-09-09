import { api } from './api.js';
import { initializeAvatarSettings } from './avatar-settings.js';
import { initializeNavigation } from './nav.js';
import { navigateTo } from './navigation.js';

export function initializeSettingsPage() {
  const settingsForm = document.querySelector('#settings-form');
  const settingsMessage = document.querySelector('#settings-message');
  const deleteAccountBtn = document.querySelector('#delete-account-btn');
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
        navigateTo('login.html');
        return;
      }

      if (settingsForm) {
        Object.entries(user).forEach(([key, value]) => {
          const input = settingsForm.querySelector(`[name="${key}"]`);
          if (input) {
            input.value = value || '';
          }
        });
      }

      avatarSettings = initializeAvatarSettings({
        apiClient: api,
        initialAvatarUrl: user.avatar_url,
        onMessage: showMessage,
        ...avatarControls,
      });
    } catch {
      navigateTo('login.html');
    }
  }

  if (settingsForm) {
    settingsForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      const formData = new FormData(settingsForm);
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
        avatarSettings?.setAvatarUrl(user.avatar_url);
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
