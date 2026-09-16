import { api } from './api.js';
import { navigateTo } from './navigation.js';

/**
 * Cinefolio - Gerenciador de Autenticação (Login e Cadastro)
 */

function initializeAuthPage() {
  // Cada página (login.html ou register.html) só tem UM desses dois
  // formulários presentes; o outro será null e simplesmente ignorado
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
    // Troca a classe CSS inteira para alternar entre estilo de
    // erro (vermelho) e sucesso (verde) usando classes do Bootstrap
    formMessage.className = `form-message alert ${isError ? 'alert-danger' : 'alert-success'} py-2 mt-3`;
    formMessage.classList.remove('d-none');   // torna a mensagem visível
  }

  // ---------------------------------------------------------------------------
  // Formulário de Login
  // ---------------------------------------------------------------------------
  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      // Impede o comportamento padrão do navegador (recarregar a página ao
      // enviar o formulário) — o envio é feito via JavaScript/fetch em vez disso
      event.preventDefault();
      const submitBtn = loginForm.querySelector('button[type="submit"]') || loginForm.querySelector('button');
      const originalText = submitBtn ? submitBtn.textContent : 'Entrar';

      // FormData lê automaticamente todos os campos do <form> pelo
      // atributo "name"; Object.fromEntries transforma isso num objeto comum
      const formData = new FormData(loginForm);
      const payload = Object.fromEntries(formData.entries());

      try {
        if (submitBtn) {
          submitBtn.disabled = true;  // evita duplo clique/envio duplicado
          submitBtn.textContent = 'Entrando...';  // feedback visual de carregamento
        }

        await api.post('/api/auth/login', payload);
        showMessage('Login realizado com sucesso! Redirecionando...', false);

        // Pequeno atraso antes de redirecionar, só para o usuário
        // conseguir LER a mensagem de sucesso antes da página mudar
        setTimeout(() => {
          navigateTo('index.html');
        }, 500);
      } catch (error) {
        showMessage(error.message, true);
        // Reabilita o botão SÓ em caso de erro — em caso de sucesso, o
        // usuário está prestes a ser redirecionado de qualquer forma
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
      // (isso é só uma conveniência de UX: o backend faz a MESMA validação
      // de verdade — nunca se pode confiar só na validação do frontend)
      if (payload.password && payload.password.length < 8) {
        showMessage('A senha deve ter pelo menos 8 caracteres.', true);
        return;
      }

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Cadastrando...';
        }

        await api.post('/api/auth/register', payload);
        showMessage('Conta criada com sucesso! Redirecionando para o login...', false);

        setTimeout(() => {
          navigateTo('login.html');
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
}

// Só inicializa depois que o HTML terminou de carregar (senão
// document.querySelector poderia não achar os elementos ainda)
document.addEventListener('DOMContentLoaded', initializeAuthPage);
