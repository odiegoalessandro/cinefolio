import assert from 'node:assert/strict';
import test from 'node:test';

async function loadNavigationModule() {
  try {
    return await import('../nav.js');
  } catch (error) {
    assert.fail(`nav.js must expose a browser-independent module: ${error.message}`);
  }
}

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
  const apiClient = {
    async get() {
      throw new Error('Sem sessão');
    },
  };

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
  assert.doesNotMatch(container.innerHTML, /<Diego>/);
  assert.match(container.innerHTML, /&lt;Diego&gt;/);
});
