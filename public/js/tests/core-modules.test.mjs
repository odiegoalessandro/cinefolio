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
    { id: 550, ignored: null },
    'https://cinefolio.test/profile.html?user=diego'
  );

  assert.equal(result, 'https://cinefolio.test/movie.html?id=550');
});

test('navigateTo updates the provided location', () => {
  const locationRef = { href: 'https://cinefolio.test/index.html' };

  navigateTo('profile.html', { user: 'diego' }, locationRef);

  assert.equal(
    locationRef.href,
    'https://cinefolio.test/profile.html?user=diego'
  );
});

test('escapeHtml escapes markup-significant characters', () => {
  assert.equal(
    escapeHtml(`<script title="'x'">&</script>`),
    '&lt;script title=&quot;&#39;x&#39;&quot;&gt;&amp;&lt;/script&gt;'
  );
  assert.equal(escapeHtml(null), '');
});

test('image helpers preserve valid values and provide fallbacks', () => {
  assert.equal(avatarImageUrl(''), 'assets/default-avatar.svg');
  assert.equal(bannerImageUrl('  '), 'assets/default-banner.svg');
  assert.equal(
    movieImageUrl('/poster.jpg'),
    'https://image.tmdb.org/t/p/w500/poster.jpg'
  );
  assert.equal(
    movieImageUrl('https://images.test/poster.jpg'),
    'https://images.test/poster.jpg'
  );
  assert.match(movieImageUrl(''), /^data:image\/svg\+xml,/);
});
