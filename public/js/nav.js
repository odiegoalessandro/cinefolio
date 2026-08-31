document.querySelector('#logout')?.addEventListener('click', async event => {
  event.preventDefault();
  try { await Api.post('/api/auth/logout', {}); App.go('index.html'); }
  catch (error) { alert(error.message); }
});

Api.get('/api/auth/me').then(({ user }) => {
  document.querySelectorAll('.auth-link').forEach(link => {
    link.href = App.page('profile.html', { user: user.username });
    link.textContent = 'Meu perfil';
  });
  document.querySelector('#logout')?.classList.remove('d-none');
}).catch(() => {});
