import assert from 'node:assert/strict';
import test from 'node:test';

async function loadNavigationModule() {
  try {
    return await import('../nav.js');
  } catch (error) {
    assert.fail(`nav.js must expose a browser-independent module: ${error.message}`);
  }
}


// Simula um "document" que nunca encontra nenhum elemento — usado para
// testar o caminho onde o usuário NÃO está logado (sem manipular DOM real)
function emptyDocument() {
  return {
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
  };
}

test('authentication failure resolves as visitor navigation', async () => {
  const { initializeNavigation } = await loadNavigationModule();
  // Simula a chamada a /api/auth/me falhando (usuário não logado)
  const apiClient = {
    async get() {
      throw new Error('Sem sessão');
    },
  };

  // assert.doesNotReject confirma que initializeNavigation trata esse
  // erro internamente (com o try/catch visto em nav.js) e NÃO deixa a
  // exceção "vazar" para quem chamou
  await assert.doesNotReject(() =>
    initializeNavigation({
      apiClient,
      documentRef: emptyDocument(),
      locationRef: { href: 'https://cinefolio.test/profile.html?user=diego' },
      alertFn() {},
    })
  );
});

test('authenticated navigation escapes the display name', async () => {
  const { initializeNavigation } = await loadNavigationModule();
  const container = { innerHTML: '' };
  const authLink = { href: '', textContent: '' };
  const documentRef = {
    querySelector(selector) {
      return selector === '#nav-auth-container' ? container : null;
    },
    querySelectorAll(selector) {
      return selector === '.auth-link' ? [authLink] : [];
    },
  };
  const apiClient = {
    async get() {
      return {
        user: {
          username: 'diego',
          // display_name propositalmente contém caracteres HTML perigosos,
          // para testar se realmente passam por escapeHtml antes de irem
          // para o innerHTML do menu
          display_name: '<Diego>',
          avatar_url: '',
        },
      };
    },
  };

  await initializeNavigation({
    apiClient,
    documentRef,
    locationRef: { href: 'https://cinefolio.test/profile.html' },
    alertFn() {},
  });

  assert.equal(authLink.textContent, 'Meu Perfil');
  assert.equal(
    authLink.href,
    'https://cinefolio.test/profile.html?user=diego'
  );

  // Confirma que o HTML "cru" e perigoso NUNCA aparece no innerHTML final
  assert.doesNotMatch(container.innerHTML, /<Diego>/);
  // E que a versão ESCAPADA (segura) é o que realmente aparece
  assert.match(container.innerHTML, /&lt;Diego&gt;/);
});
