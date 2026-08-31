async function setupSettings() {
  try {
    const { user } = await Api.get('/api/auth/me');
    for (const [key, value] of Object.entries(user)) {
      const input = document.querySelector(`[name="${key}"]`);
      if (input) input.value = value || '';
    }
  } catch { App.go('login.html'); }
}

document.querySelector('#settings-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  try { await Api.put('/api/profile', Object.fromEntries(new FormData(event.target))); document.querySelector('#settings-message').textContent = 'Perfil atualizado.'; }
  catch (error) { document.querySelector('#settings-message').textContent = error.message; }
});

document.querySelector('#delete-account')?.addEventListener('click', async () => {
  if (!confirm('Excluir sua conta e todos os dados?')) return;
  try { await Api.delete('/api/account'); App.go('index.html'); }
  catch (error) { document.querySelector('#settings-message').textContent = error.message; }
});

setupSettings();
