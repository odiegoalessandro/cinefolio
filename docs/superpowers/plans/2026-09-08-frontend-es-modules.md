# Native Frontend Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Replace implicit frontend globals and script-order coupling with native browser modules while preserving every page behavior and public profile access.

**Architecture:** Shared browser concerns become focused ES modules with named exports. Each HTML page loads a classic file-protocol guard and one module entrypoint; that entrypoint imports navigation and page dependencies explicitly.

**Tech Stack:** Browser-native ES Modules, vanilla JavaScript, Node 24 built-in test runner, Python 3 standard-library HTTP server and unittest.

**Spec:** docs/superpowers/specs/2026-09-08-frontend-es-modules-design.md

## Global Constraints

- Use only native browser ES Modules.
- Do not add npm, a bundler, a frontend framework, or a runtime dependency.
- Keep the Python backend as the static-file server.
- Preserve current layout, endpoints, rules, messages, and API contracts.
- Keep profile.html?user=<username> accessible without a session cookie.
- Do not publish application values on window or globalThis.
- Keep every module import at the top of its file.
- Keep file:// guidance functional through a classic script.

## File Map

**Create**

- public/js/navigation.js: page URL creation and redirects.
- public/js/html-escaping.js: HTML text escaping.
- public/js/images.js: avatar, banner, and TMDB image normalization.
- public/js/file-protocol-guard.js: classic file:// guidance.
- public/js/tests/core-modules.test.mjs: pure shared-module tests.
- public/js/tests/api.test.mjs: HTTP client tests.
- public/js/tests/file-protocol-guard.test.mjs: executed guard tests.
- public/js/tests/nav.test.mjs: navigation component tests.
- public/js/tests/page-entrypoints.test.mjs: module-graph smoke tests.
- server/tests/test_frontend_assets.py: served-page and public-profile tests.

**Modify**

- public/js/api.js: side-effect-free HTTP client module.
- public/js/nav.js: explicitly initialized navigation module.
- public/js/auth.js: login/register module entrypoint.
- public/js/search.js: catalog module entrypoint.
- public/js/movie.js: movie-details module entrypoint.
- public/js/profile.js: public-profile module entrypoint.
- public/js/settings.js: settings module entrypoint.
- public/index.html
- public/login.html
- public/register.html
- public/movie.html
- public/profile.html
- public/settings.html
- README.md

---

### Task 1: Pure shared modules

**Files:**

- Create: public/js/navigation.js
- Create: public/js/html-escaping.js
- Create: public/js/images.js
- Create: public/js/tests/core-modules.test.mjs

**Interfaces:**

- Produces: createPageUrl(pageName, params, baseUrl) -> string
- Produces: navigateTo(pageName, params, locationRef) -> void
- Produces: escapeHtml(value) -> string
- Produces: avatarImageUrl(url) -> string
- Produces: bannerImageUrl(url) -> string
- Produces: movieImageUrl(path) -> string

- [ ] **Step 1: Write the failing shared-module tests**

Create public/js/tests/core-modules.test.mjs:

~~~js
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
~~~

- [ ] **Step 2: Run the tests and confirm RED**

Run:

~~~bash
node --test public/js/tests/core-modules.test.mjs
~~~

Expected: FAIL with ERR_MODULE_NOT_FOUND for the first missing shared module.

- [ ] **Step 3: Implement navigation.js**

~~~js
export function createPageUrl(
  pageName,
  params = {},
  baseUrl = globalThis.location.href
) {
  const url = new URL(pageName, baseUrl);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });

  return url.href;
}

export function navigateTo(
  pageName,
  params = {},
  locationRef = globalThis.location
) {
  locationRef.href = createPageUrl(pageName, params, locationRef.href);
}
~~~

- [ ] **Step 4: Implement html-escaping.js**

~~~js
const HTML_ENTITIES = Object.freeze({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
});

export function escapeHtml(value) {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value).replace(
    /[&<>'"]/g,
    (character) => HTML_ENTITIES[character]
  );
}
~~~

- [ ] **Step 5: Implement images.js**

Move the current fallback SVG from api.js without changing its bytes:

~~~js
const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500';
const EMPTY_MOVIE_IMAGE =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="500" height="750"%3E%3Crect width="100%25" height="100%25" fill="%231a1c24"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%23737787" font-family="sans-serif" font-size="20"%3ESem Imagem%3C/text%3E%3C/svg%3E';

export function avatarImageUrl(url) {
  return (url || '').trim() || 'assets/default-avatar.svg';
}

export function bannerImageUrl(url) {
  return (url || '').trim() || 'assets/default-banner.svg';
}

export function movieImageUrl(path) {
  if (!path) {
    return EMPTY_MOVIE_IMAGE;
  }

  return /^https?:\/\//i.test(path)
    ? path
    : `${TMDB_IMAGE_BASE_URL}${path}`;
}
~~~

- [ ] **Step 6: Run the tests and confirm GREEN**

Run:

~~~bash
node --test public/js/tests/core-modules.test.mjs
~~~

Expected: 4 tests pass.

- [ ] **Step 7: Commit**

~~~bash
git add public/js/navigation.js public/js/html-escaping.js public/js/images.js public/js/tests/core-modules.test.mjs
git commit -m "refactor: extract frontend utility modules"
~~~

---

### Task 2: HTTP client and file-protocol guard

**Files:**

- Modify: public/js/api.js
- Create: public/js/file-protocol-guard.js
- Create: public/js/tests/api.test.mjs
- Create: public/js/tests/file-protocol-guard.test.mjs

**Interfaces:**

- Consumes: no browser globals during module evaluation.
- Produces: createApiClient(fetchImpl) -> frozen client object.
- Produces: api with get, post, put, and delete methods.
- Produces: a classic guard with no exported or global identifiers.

- [ ] **Step 1: Write failing API client tests**

Create public/js/tests/api.test.mjs:

~~~js
import assert from 'node:assert/strict';
import test from 'node:test';

async function loadApiModule() {
  try {
    return await import('../api.js');
  } catch (error) {
    assert.fail(`api.js must be importable without a browser: ${error.message}`);
  }
}

function response({ ok = true, body = '' } = {}) {
  return {
    ok,
    async text() {
      return body;
    },
  };
}

test('get sends JSON headers and returns parsed data', async () => {
  const { createApiClient } = await loadApiModule();
  const calls = [];
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"results":[1]}' });
  });

  const result = await client.get('/api/movies/popular');

  assert.deepEqual(result, { results: [1] });
  assert.deepEqual(calls, [
    {
      path: '/api/movies/popular',
      options: {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      },
    },
  ]);
});

test('post serializes its body as JSON', async () => {
  const { createApiClient } = await loadApiModule();
  const calls = [];
  const client = createApiClient(async (path, options) => {
    calls.push({ path, options });
    return response({ body: '{"ok":true}' });
  });

  await client.post('/api/auth/login', { username: 'diego' });

  assert.equal(calls[0].options.body, '{"username":"diego"}');
  assert.equal(calls[0].options.method, 'POST');
});

test('API errors preserve the server message', async () => {
  const { createApiClient } = await loadApiModule();
  const client = createApiClient(async () =>
    response({ ok: false, body: '{"error":"Credenciais inválidas."}' })
  );

  await assert.rejects(
    client.post('/api/auth/login', {}),
    /Credenciais inválidas\./
  );
});

test('successful non-JSON responses become an empty object', async () => {
  const { createApiClient } = await loadApiModule();
  const client = createApiClient(async () => response({ body: 'plain text' }));

  assert.deepEqual(await client.get('/api/example'), {});
});
~~~

- [ ] **Step 2: Write failing guard tests**

Create public/js/tests/file-protocol-guard.test.mjs:

~~~js
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

async function executeGuard(protocol) {
  const source = await readFile(
    new URL('../file-protocol-guard.js', import.meta.url),
    'utf-8'
  );
  const documentRef = {
    body: { innerHTML: '' },
    addEventListener(eventName, listener) {
      if (eventName === 'DOMContentLoaded') {
        this.readyListener = listener;
      }
    },
  };

  vm.runInNewContext(source, {
    document: documentRef,
    window: { location: { protocol } },
  });

  return documentRef;
}

test('file protocol renders server startup guidance', async () => {
  const documentRef = await executeGuard('file:');

  documentRef.readyListener();

  assert.match(documentRef.body.innerHTML, /python -m server/);
  assert.match(documentRef.body.innerHTML, /http:\/\/127\.0\.0\.1:8000/);
});

test('HTTP protocol leaves the page untouched', async () => {
  const documentRef = await executeGuard('http:');

  assert.equal(documentRef.readyListener, undefined);
  assert.equal(documentRef.body.innerHTML, '');
});
~~~

- [ ] **Step 3: Run both test files and confirm RED**

Run:

~~~bash
node --test public/js/tests/api.test.mjs public/js/tests/file-protocol-guard.test.mjs
~~~

Expected: FAIL because api.js evaluates window at import time and file-protocol-guard.js does not exist.

- [ ] **Step 4: Replace api.js with a side-effect-free module**

~~~js
const JSON_HEADERS = Object.freeze({
  'Content-Type': 'application/json',
  Accept: 'application/json',
});

export function createApiClient(fetchImpl = globalThis.fetch) {
  async function request(path, options = {}) {
    const response = await fetchImpl(path, {
      ...options,
      headers: {
        ...JSON_HEADERS,
        ...(options.headers || {}),
      },
    });
    const rawText = await response.text();

    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = {};
    }

    if (!response.ok) {
      if (rawText.includes('Cannot GET') || rawText.includes('Cannot POST')) {
        throw new Error(
          'O frontend foi aberto no servidor errado. Use python -m server e abra http://127.0.0.1:8000.'
        );
      }

      throw new Error(data.error || 'Não foi possível concluir a operação.');
    }

    return data;
  }

  return Object.freeze({
    get(path) {
      return request(path, { method: 'GET' });
    },
    post(path, body) {
      return request(path, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },
    put(path, body) {
      return request(path, {
        method: 'PUT',
        body: JSON.stringify(body),
      });
    },
    delete(path) {
      return request(path, { method: 'DELETE' });
    },
  });
}

export const api = createApiClient();
~~~

- [ ] **Step 5: Move the file:// UI into file-protocol-guard.js**

Use an IIFE so the classic script creates no global identifier:

~~~js
(() => {
  if (window.location.protocol !== 'file:') {
    return;
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.innerHTML = `
      <main class="form-center-page">
        <div class="panel-card text-center">
          <h1 class="panel-title text-danger">Atenção</h1>
          <p class="panel-subtitle">Esta aplicação precisa do backend Python para funcionar.</p>
          <div class="alert alert-warning text-start">
            <p class="mb-2"><strong>Como iniciar:</strong></p>
            <code>python -m server</code>
            <p class="mt-2 mb-0">Depois acesse no navegador: <strong>http://127.0.0.1:8000</strong></p>
          </div>
        </div>
      </main>
    `;
  });
})();
~~~

- [ ] **Step 6: Run both test files and confirm GREEN**

Run:

~~~bash
node --test public/js/tests/api.test.mjs public/js/tests/file-protocol-guard.test.mjs
~~~

Expected: 6 tests pass.

- [ ] **Step 7: Commit**

~~~bash
git add public/js/api.js public/js/file-protocol-guard.js public/js/tests/api.test.mjs public/js/tests/file-protocol-guard.test.mjs
git commit -m "refactor: isolate frontend HTTP client"
~~~

---

### Task 3: Navigation component

**Files:**

- Modify: public/js/nav.js
- Create: public/js/tests/nav.test.mjs

**Interfaces:**

- Consumes: api, createPageUrl, navigateTo, avatarImageUrl, and escapeHtml.
- Produces: initializeNavigation(options) -> Promise<void>.
- Guarantees: missing or invalid authentication resolves as visitor navigation.

- [ ] **Step 1: Write failing navigation tests**

Create public/js/tests/nav.test.mjs:

~~~js
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
~~~

- [ ] **Step 2: Run the navigation tests and confirm RED**

Run:

~~~bash
node --test public/js/tests/nav.test.mjs
~~~

Expected: FAIL because current nav.js evaluates document immediately and exports no initializer.

- [ ] **Step 3: Convert nav.js into an explicitly initialized module**

Place this import block at the top:

~~~js
import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { avatarImageUrl } from './images.js';
import { createPageUrl, navigateTo } from './navigation.js';
~~~

Expose this exact boundary:

~~~js
export async function initializeNavigation({
  apiClient = api,
  documentRef = globalThis.document,
  locationRef = globalThis.location,
  alertFn = globalThis.alert,
} = {}) {
~~~

Inside that function:

1. Query all elements through documentRef.
2. Replace Api.get and Api.post with apiClient.get and apiClient.post.
3. Replace App.page with createPageUrl and pass locationRef.href as base URL.
4. Replace App.go with navigateTo and pass locationRef.
5. Replace profileImageUrl with avatarImageUrl.
6. Keep escapeHtml imported from html-escaping.js.
7. Reuse one async logout handler for static and dynamically rendered buttons.
8. Wrap the session lookup and authenticated rendering in try/catch; return from
   catch without throwing so visitors remain on public pages.
9. Remove the DOMContentLoaded listener from nav.js.

The logout handler must preserve the current visible error:

~~~js
const handleLogout = async (event) => {
  event?.preventDefault();

  try {
    await apiClient.post('/api/auth/logout', {});
    navigateTo('index.html', {}, locationRef);
  } catch (error) {
    alertFn(`Erro ao sair: ${error.message}`);
  }
};
~~~

- [ ] **Step 4: Run the navigation tests and confirm GREEN**

Run:

~~~bash
node --test public/js/tests/nav.test.mjs
~~~

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

~~~bash
git add public/js/nav.js public/js/tests/nav.test.mjs
git commit -m "refactor: make navigation dependencies explicit"
~~~

---

### Task 4: Page entrypoints, HTML wiring, and public profile

**Files:**

- Modify: public/js/auth.js
- Modify: public/js/search.js
- Modify: public/js/movie.js
- Modify: public/js/profile.js
- Modify: public/js/settings.js
- Modify: public/index.html
- Modify: public/login.html
- Modify: public/register.html
- Modify: public/movie.html
- Modify: public/profile.html
- Modify: public/settings.html
- Create: public/js/tests/page-entrypoints.test.mjs
- Create: server/tests/test_frontend_assets.py

**Interfaces:**

- Consumes: all shared modules from Tasks 1 to 3.
- Produces: one ESM entrypoint per HTML page.
- Guarantees: profile initialization does not await or require navigation auth.

- [ ] **Step 1: Write the failing served-asset and public-profile tests**

Create server/tests/test_frontend_assets.py:

~~~python
"""Testes dos assets ESM servidos e do acesso público ao perfil."""

import json
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from server.config import ServerConfig
from server.database.connection import get_connection, initialize_database
from server.main import create_server
from server.repositories.user_repository import UserRepository
from server.services.auth_service import hash_password


PAGE_ENTRYPOINTS = {
    "index.html": "js/search.js",
    "login.html": "js/auth.js",
    "register.html": "js/auth.js",
    "movie.html": "js/movie.js",
    "profile.html": "js/profile.js",
    "settings.html": "js/settings.js",
}


class LocalScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return

        attributes = dict(attrs)
        source = attributes.get("src", "")
        if source.startswith("js/"):
            self.scripts.append((source, attributes.get("type")))


class FrontendAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_dir.name) / "cinefolio.sqlite3"
        initialize_database(database_path)

        connection = get_connection(database_path)
        try:
            UserRepository(connection).create(
                username="public_user",
                display_name="Perfil Público",
                password_hash=hash_password("senhasegura123"),
            )
        finally:
            connection.close()

        cls.server = create_server(
            ServerConfig(host="127.0.0.1", port=0),
            database_path=database_path,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()

    def test_each_page_serves_guard_and_one_module_entrypoint(self):
        for page, entrypoint in PAGE_ENTRYPOINTS.items():
            with self.subTest(page=page):
                with urlopen(f"{self.base_url}/{page}", timeout=2) as response:
                    html = response.read().decode("utf-8")

                parser = LocalScriptParser()
                parser.feed(html)
                self.assertEqual(
                    parser.scripts,
                    [
                        ("js/file-protocol-guard.js", None),
                        (entrypoint, "module"),
                    ],
                )

                for source, _ in parser.scripts:
                    with urlopen(
                        f"{self.base_url}/{source}",
                        timeout=2,
                    ) as asset_response:
                        asset_response.read()

                    self.assertEqual(asset_response.status, 200)
                    self.assertIn(
                        asset_response.headers.get_content_type(),
                        {"text/javascript", "application/javascript"},
                    )

    def test_profile_data_is_public_without_session_cookie(self):
        with urlopen(
            f"{self.base_url}/api/profiles/public_user",
            timeout=2,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["profile"]["username"], "public_user")
~~~

- [ ] **Step 2: Write the module-graph smoke test**

Create public/js/tests/page-entrypoints.test.mjs:

~~~js
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
~~~

- [ ] **Step 3: Run the new tests and confirm RED**

Run:

~~~bash
python -m unittest server.tests.test_frontend_assets -v
node --test public/js/tests/page-entrypoints.test.mjs
~~~

Expected: the Python suite FAILS because each current page serves api.js and
nav.js as additional classic scripts. The public-profile test may already pass
and becomes a regression guard.

- [ ] **Step 4: Convert auth.js**

Add imports at the top:

~~~js
import { api } from './api.js';
import { navigateTo } from './navigation.js';
~~~

Rename the DOMContentLoaded callback body to a local initializeAuthPage
function. Apply these exact substitutions:

- Api.post -> api.post
- App.go('index.html') -> navigateTo('index.html')
- App.go('login.html') -> navigateTo('login.html')

Register the entrypoint at the bottom:

~~~js
document.addEventListener('DOMContentLoaded', initializeAuthPage);
~~~

- [ ] **Step 5: Convert search.js**

Add imports at the top:

~~~js
import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { movieImageUrl } from './images.js';
import { initializeNavigation } from './nav.js';
import { createPageUrl } from './navigation.js';
~~~

Rename the current callback body to initializeSearchPage. Apply:

- Api.get -> api.get
- imageUrl -> movieImageUrl
- App.page -> createPageUrl

Use this bottom-level registration:

~~~js
document.addEventListener('DOMContentLoaded', () => {
  void initializeNavigation();
  initializeSearchPage();
});
~~~

- [ ] **Step 6: Convert movie.js**

Add imports at the top:

~~~js
import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import { movieImageUrl } from './images.js';
import { initializeNavigation } from './nav.js';
~~~

Rename the current callback body to initializeMoviePage. Apply:

- Api.get -> api.get
- Api.put -> api.put
- Api.delete -> api.delete
- imageUrl -> movieImageUrl

Use:

~~~js
document.addEventListener('DOMContentLoaded', () => {
  void initializeNavigation();
  initializeMoviePage();
});
~~~

- [ ] **Step 7: Convert profile.js without coupling it to auth**

Add imports at the top:

~~~js
import { api } from './api.js';
import { escapeHtml } from './html-escaping.js';
import {
  avatarImageUrl,
  bannerImageUrl,
  movieImageUrl,
} from './images.js';
import { initializeNavigation } from './nav.js';
import { createPageUrl } from './navigation.js';
~~~

Rename the current callback body to initializeProfilePage. Apply:

- Api.get -> api.get
- App.page -> createPageUrl
- profileImageUrl -> avatarImageUrl
- bannerImageUrl remains bannerImageUrl
- imageUrl -> movieImageUrl

Start both concerns independently:

~~~js
document.addEventListener('DOMContentLoaded', () => {
  void initializeNavigation();
  initializeProfilePage();
});
~~~

Do not await initializeNavigation and do not inspect /api/auth/me inside
initializeProfilePage. Profile data must still come directly from:

~~~js
api.get(`/api/profiles/${encodeURIComponent(username)}`)
~~~

- [ ] **Step 8: Convert settings.js**

Add imports at the top:

~~~js
import { api } from './api.js';
import { initializeNavigation } from './nav.js';
import { navigateTo } from './navigation.js';
~~~

Rename the current callback body to initializeSettingsPage. Apply:

- Api.get -> api.get
- Api.put -> api.put
- Api.delete -> api.delete
- App.go -> navigateTo

Use:

~~~js
document.addEventListener('DOMContentLoaded', () => {
  void initializeNavigation();
  initializeSettingsPage();
});
~~~

- [ ] **Step 9: Replace local script tags in every HTML page**

Keep the Bootstrap script unchanged. Replace all local script tags with the
exact pair from this table:

| HTML | Classic guard | Module entrypoint |
| --- | --- | --- |
| public/index.html | js/file-protocol-guard.js | js/search.js |
| public/login.html | js/file-protocol-guard.js | js/auth.js |
| public/register.html | js/file-protocol-guard.js | js/auth.js |
| public/movie.html | js/file-protocol-guard.js | js/movie.js |
| public/profile.html | js/file-protocol-guard.js | js/profile.js |
| public/settings.html | js/file-protocol-guard.js | js/settings.js |

The resulting local tags must use this form:

~~~html
<script src="js/file-protocol-guard.js"></script>
<script type="module" src="js/ENTRYPOINT.js"></script>
~~~

Replace ENTRYPOINT.js with the table value; do not keep api.js or nav.js tags.

- [ ] **Step 10: Run migration tests and confirm GREEN**

Run:

~~~bash
python -m unittest server.tests.test_frontend_assets -v
node --test public/js/tests/page-entrypoints.test.mjs
~~~

Expected: 2 Python tests and 6 Node tests pass.

- [ ] **Step 11: Run all frontend tests**

~~~bash
node --test public/js/tests/*.test.mjs
~~~

Expected: all frontend tests pass with no warnings or unhandled rejections.

- [ ] **Step 12: Commit**

~~~bash
git add public server/tests/test_frontend_assets.py
git commit -m "refactor: migrate frontend to native modules"
~~~

---

### Task 5: Documentation and full verification

**Files:**

- Modify: README.md

**Interfaces:**

- Consumes: final module layout and all test commands.
- Produces: accurate setup, architecture, and test documentation.

- [ ] **Step 1: Update the README tree**

Replace the public/js subsection with:

~~~text
│   └── js/
│       ├── api.js                 # Cliente HTTP
│       ├── navigation.js          # URLs e redirecionamentos
│       ├── html-escaping.js       # Escape para interpolação HTML
│       ├── images.js              # URLs e fallbacks de imagens
│       ├── file-protocol-guard.js # Orientação para file://
│       ├── nav.js                 # Barra de navegação
│       ├── auth.js                # Entrypoint de login e cadastro
│       ├── movie.js               # Entrypoint de detalhes
│       ├── profile.js             # Entrypoint de perfil público
│       ├── search.js              # Entrypoint do catálogo
│       ├── settings.js            # Entrypoint de configurações
│       └── tests/                 # Testes Node sem dependências
~~~

Add the JavaScript test command beside the Python commands:

~~~bash
node --test public/js/tests/*.test.mjs
~~~

- [ ] **Step 2: Run the complete JavaScript suite**

~~~bash
node --test public/js/tests/*.test.mjs
~~~

Expected: every JavaScript unit and smoke test passes.

- [ ] **Step 3: Check every JavaScript file**

~~~bash
find public/js -type f -name '*.js' -print0 | xargs -0 -n1 node --check
find public/js/tests -type f -name '*.mjs' -print0 | xargs -0 -n1 node --check
~~~

Expected: both commands exit 0.

- [ ] **Step 4: Run the complete Python suite**

~~~bash
python -m unittest discover -s server/tests -v
python -m compileall -q server
~~~

Expected: all tests pass and compileall exits 0.

- [ ] **Step 5: Verify architectural constraints**

~~~bash
test ! -e package.json
! rg -n '\b(Api|App)\.' public/js
! rg -n '<script src="js/(api|nav|auth|search|movie|profile|settings)\.js"' public/*.html
git diff --check
~~~

Expected: every command exits 0 and no legacy global or classic application
script reference is reported.

- [ ] **Step 6: Review the complete diff**

~~~bash
git status --short
git diff --stat origin/master...HEAD
git diff origin/master...HEAD -- public README.md server/tests
~~~

Confirm line by line:

- Imports are at the top of every module.
- No page layout or API path changed.
- profile.js starts profile loading independently from navigation.
- All six HTML files contain the guard and exactly one module entrypoint.
- No package manager or build configuration was added.

- [ ] **Step 7: Commit**

~~~bash
git add README.md
git commit -m "docs: document native frontend modules"
~~~

- [ ] **Step 8: Re-run final verification on the committed tree**

~~~bash
node --test public/js/tests/*.test.mjs
python -m unittest discover -s server/tests -v
python -m compileall -q server
git status --short --branch
~~~

Expected: both suites pass, compilation exits 0, and the branch is clean.
