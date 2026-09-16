import assert from 'node:assert/strict';
import test from 'node:test';

// Este arquivo testa uma coisa bem específica: que cada módulo "principal"
// de página (search.js, auth.js, movie.js etc) realmente registra o
// listener "DOMContentLoaded" quando importado — ou seja, que o "encanamento"
// de inicialização de cada página está correto.

// Como esses módulos de página usam "document", "window", "alert" e
// "confirm" GLOBAIS (não são passados como parâmetro, diferente de nav.js),
// é preciso simular esses globais ANTES de importar qualquer um deles
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

// Mapeia cada página HTML para o módulo JS que deveria ser o "ponto de
// entrada" dela (mesmo mapeamento verificado no lado do servidor em
// test_frontend_assets.py, mas aqui testado do lado do módulo JS puro)
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
    // O "?page=..." na URL do import é um truque para o Node.js tratar
    // cada import como um MÓDULO DIFERENTE (evita cache), já que
    // login.html e register.html apontam para o MESMO arquivo auth.js —
    // sem isso, o segundo import seria ignorado (Node só executa um
    // módulo uma vez por padrão)
    const moduleUrl = new URL(
      `../${entrypoint}?page=${encodeURIComponent(page)}`,
      import.meta.url
    );

    await import(moduleUrl);

    // Confirma que exatamente 1 NOVO listener "DOMContentLoaded" foi
    // registrado como resultado desse import
    assert.equal(listeners.length, listenerCount + 1);
    assert.equal(listeners.at(-1).eventName, 'DOMContentLoaded');
  });
}
