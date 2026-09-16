// Runner de testes nativo do Node.js (node:test) — não precisa de
// biblioteca externa como Jest para rodar estes testes
import assert from 'node:assert/strict';
import test from 'node:test';

import { escapeHtml } from '../html-escaping.js';
import {
  avatarImageUrl,
  bannerImageUrl,
  movieImageUrl,
} from '../images.js';
import { createPageUrl, navigateTo } from '../navigation.js';

test('createPageUrl resolves a page and omits nullish parameters', () => {
  const result = createPageUrl(
    'movie.html',
    { id: 550, ignored: null }, // "ignored: null" testa que parâmetros nulos são descartados
    'https://cinefolio.test/profile.html?user=diego'
  );

  assert.equal(result, 'https://cinefolio.test/movie.html?id=550');
});

test('navigateTo updates the provided location', () => {
  // Um objeto simples simula "location" sem precisar de um navegador real
  const locationRef = { href: 'https://cinefolio.test/index.html' };

  navigateTo('profile.html', { user: 'diego' }, locationRef);

  assert.equal(
    locationRef.href,
    'https://cinefolio.test/profile.html?user=diego'
  );
});

test('escapeHtml escapes markup-significant characters', () => {
  // Testa TODOS os caracteres perigosos de uma vez: <, >, ", ', &
  assert.equal(
    escapeHtml(`<script title="'x'">&</script>`),
    '&lt;script title=&quot;&#39;x&#39;&quot;&gt;&amp;&lt;/script&gt;'
  );
  // Testa o caso especial de entrada nula (não deve quebrar, retorna string vazia)
  assert.equal(escapeHtml(null), '');
});


test('image helpers preserve valid values and provide fallbacks', () => {
  assert.equal(avatarImageUrl(''), 'assets/default-avatar.svg');
  assert.equal(bannerImageUrl('  '), 'assets/default-banner.svg');
  assert.equal(
    movieImageUrl('/poster.jpg'),
    'https://image.tmdb.org/t/p/w500/poster.jpg'
  );

  // URL já completa (de outro domínio) deve ser usada como está, sem
  // concatenar com a base da TMDB
  assert.equal(
    movieImageUrl('https://images.test/poster.jpg'),
    'https://images.test/poster.jpg'
  );
  // Caminho vazio deve gerar a imagem placeholder embutida (SVG data URI)
  assert.match(movieImageUrl(''), /^data:image\/svg\+xml,/);
});
