import assert from 'node:assert/strict';
import test from 'node:test';

const listeners = [];
globalThis.document = {
  addEventListener(eventName, listener) {
    listeners.push({ eventName, listener });
  },
};
globalThis.location = {
  href: 'https://cinefolio.test/index.html',
  protocol: 'https:',
};
globalThis.window = {
  alert() {},
  confirm() {
    return false;
  },
  location: globalThis.location,
};
globalThis.alert = globalThis.window.alert;
globalThis.confirm = globalThis.window.confirm;

const pages = [
  ['index.html', 'search.js'],
  ['login.html', 'auth.js'],
  ['register.html', 'auth.js'],
  ['movie.html', 'movie.js'],
  ['profile.html', 'profile.js'],
  ['settings.html', 'settings.js'],
];

for (const [page, entrypoint] of pages) {
  test(`${page} loads its module graph`, async () => {
    const listenerCount = listeners.length;
    const moduleUrl = new URL(
      `../${entrypoint}?page=${encodeURIComponent(page)}`,
      import.meta.url
    );

    await import(moduleUrl);

    assert.equal(listeners.length, listenerCount + 1);
    assert.equal(listeners.at(-1).eventName, 'DOMContentLoaded');
  });
}
