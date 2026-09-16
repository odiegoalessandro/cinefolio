import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

// Roda o script file-protocol-guard.js dentro de um ambiente JS ISOLADO
// (node:vm), com apenas "document" e "window" simulados — não usa o
// require/import normal porque o script original não é um módulo ES
// (não tem "export"), é um script "solto" pensado para rodar direto no navegador
async function executeGuard(protocol) {
  const source = await readFile(
    new URL('../file-protocol-guard.js', import.meta.url),
    'utf-8'
  );
  const documentRef = {
    body: { innerHTML: '' },
    addEventListener(eventName, listener) {
      // Só guarda a referência do listener "DOMContentLoaded" para o
      // teste poder chamá-lo manualmente depois (vm não dispara eventos reais)
      if (eventName === 'DOMContentLoaded') {
        this.readyListener = listener;
      }
    },
  };

  // Executa o código-fonte do script dentro do contexto falso criado acima
  vm.runInNewContext(source, {
    document: documentRef,
    window: { location: { protocol } },
  });

  return documentRef;
}

test('file protocol renders server startup guidance', async () => {
  const documentRef = await executeGuard('file:');

  // Simula o navegador disparando o evento DOMContentLoaded
  documentRef.readyListener();

  assert.match(documentRef.body.innerHTML, /python -m server/);
  assert.match(documentRef.body.innerHTML, /http:\/\/127\.0\.0\.1:8000/);
});

test('HTTP protocol leaves the page untouched', async () => {
  const documentRef = await executeGuard('http:');

  // Quando o protocolo é http:, o guard.js retorna cedo (ver o "return"
  // dentro do if) e NUNCA chega a registrar o listener
  assert.equal(documentRef.readyListener, undefined);
  assert.equal(documentRef.body.innerHTML, '');
});
