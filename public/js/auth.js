document.querySelector('#login-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  const form = Object.fromEntries(new FormData(event.target));
  try { await Api.post('/api/auth/login', form); App.go('index.html'); }
  catch (error) { showMessage(error.message); }
});

document.querySelector('#register-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  const form = Object.fromEntries(new FormData(event.target));
  try { await Api.post('/api/auth/register', form); App.go('login.html'); }
  catch (error) { showMessage(error.message); }
});

function showMessage(message) { document.querySelector('.form-message').textContent = message; }
