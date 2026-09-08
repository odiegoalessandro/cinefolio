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
