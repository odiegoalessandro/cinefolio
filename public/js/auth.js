/**
 * Cinefolio - Gerenciador de Autenticação (Login e Cadastro)
 */

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.querySelector('#login-form');
  const registerForm = document.querySelector('#register-form');
  const formMessage = document.querySelector('.form-message');

  /**
   * Exibe mensagens de feedback (erro ou sucesso) no formulário.
   * @param {string} message - Mensagem a ser exibida.
   * @param {boolean} isError - Define se a mensagem é de erro.
   */
  function showMessage(message, isError = true) {
    if (!formMessage) return;
    formMessage.textContent = message;
    formMessage.className = `form-message alert ${isError ? 'alert-danger' : 'alert-success'} py-2 mt-3`;
    formMessage.classList.remove('d-none');
  }

  // ---------------------------------------------------------------------------
  // Formulário de Login
  // ---------------------------------------------------------------------------
  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submitBtn = loginForm.querySelector('button[type="submit"]') || loginForm.querySelector('button');
      const originalText = submitBtn ? submitBtn.textContent : 'Entrar';

      const formData = new FormData(loginForm);
      const payload = Object.fromEntries(formData.entries());

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Entrando...';
        }

        await Api.post('/api/auth/login', payload);
        showMessage('Login realizado com sucesso! Redirecionando...', false);

        setTimeout(() => {
          App.go('index.html');
        }, 500);
      } catch (error) {
        showMessage(error.message, true);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Formulário de Registro / Cadastro
  // ---------------------------------------------------------------------------
  if (registerForm) {
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submitBtn = registerForm.querySelector('button[type="submit"]') || registerForm.querySelector('button');
      const originalText = submitBtn ? submitBtn.textContent : 'Cadastrar';

      const formData = new FormData(registerForm);
      const payload = Object.fromEntries(formData.entries());

      // Validações básicas no cliente
      if (payload.password && payload.password.length < 8) {
        showMessage('A senha deve ter pelo menos 8 caracteres.', true);
        return;
      }

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Cadastrando...';
        }

        await Api.post('/api/auth/register', payload);
        showMessage('Conta criada com sucesso! Redirecionando para o login...', false);

        setTimeout(() => {
          App.go('login.html');
        }, 1000);
      } catch (error) {
        showMessage(error.message, true);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }
});
