# Migração do frontend para ES Modules nativos

## Objetivo

Eliminar as dependências globais e a dependência implícita da ordem das tags
`<script>` no frontend do Cinefolio. Cada script deve declarar suas dependências
por imports no topo, sem alterar layout, endpoints ou regras de negócio.

## Restrições

- Usar somente ES Modules nativos do navegador.
- Não adicionar npm, bundler, framework ou dependência de runtime.
- Manter o backend Python como servidor dos arquivos estáticos.
- Preservar os fluxos e mensagens existentes.
- Continuar orientando o usuário que abrir um HTML via `file://`.

## Arquitetura

### Módulos compartilhados

- `public/js/api.js`: cliente HTTP e métodos `get`, `post`, `put` e `delete`.
- `public/js/navigation.js`: criação de URLs internas e redirecionamentos.
- `public/js/html-escaping.js`: escape de valores interpolados em HTML.
- `public/js/images.js`: normalização das URLs de avatar, banner e filmes.
- `public/js/nav.js`: inicialização e atualização da barra de navegação.
- `public/js/file-protocol-guard.js`: aviso executado como script clássico
  quando uma página for aberta diretamente pelo sistema de arquivos.

Os módulos não publicarão valores em `window` ou `globalThis`.

### Entrypoints das páginas

Os arquivos existentes continuarão sendo os entrypoints:

| Página | Entrypoint | Inicializa navegação |
| --- | --- | --- |
| `index.html` | `search.js` | Sim |
| `login.html` | `auth.js` | Não |
| `register.html` | `auth.js` | Não |
| `movie.html` | `movie.js` | Sim |
| `profile.html` | `profile.js` | Sim |
| `settings.html` | `settings.js` | Sim |

Cada HTML carregará o guard clássico e somente um entrypoint com
`type="module"`. Os entrypoints importarão diretamente tudo o que utilizarem.

`profile.html?user=<username>` continuará público. A inicialização da barra de
navegação poderá consultar a sessão atual para personalizar os links, mas não
poderá exigir autenticação nem bloquear a busca e a renderização do perfil.

## Fluxo de execução

1. `file-protocol-guard.js` registra o aviso para acessos via `file://`.
2. O navegador resolve o grafo de módulos do entrypoint.
3. No `DOMContentLoaded`, o entrypoint inicializa a navegação quando aplicável.
4. O entrypoint inicializa a lógica específica da página sem depender da
   conclusão da navegação.
5. Requisições passam pelo cliente de `api.js` e chegam às rotas `/api/*`.
6. A página trata sucesso ou falha e atualiza o DOM.

## Tratamento de erros e segurança

- O cliente HTTP continuará lançando `Error` com a mensagem retornada pela API
  ou com a mensagem genérica atual.
- Respostas vazias ou não JSON continuarão sendo normalizadas para objeto vazio.
- Os entrypoints continuarão responsáveis por apresentar erros no contexto da
  própria tela.
- A ausência de sessão será tratada como navegação de visitante nas páginas
  públicas, incluindo o perfil.
- Dados externos continuarão passando por `escapeHtml` antes de qualquer
  interpolação em HTML.
- URLs de imagem continuarão passando pelos normalizadores de `images.js`.
- O guard de `file://` continuará fora do grafo ESM, pois o navegador pode
  bloquear módulos locais antes que eles consigam exibir orientação.

## Estratégia de migração

1. Criar testes dos contratos públicos dos módulos compartilhados.
2. Extrair navegação, escape de HTML, imagens e comunicação HTTP de `api.js`.
3. Converter `nav.js` para um módulo com inicialização explícita.
4. Converter cada script de página para imports explícitos.
5. Atualizar cada HTML para carregar o guard e um único entrypoint ESM.
6. Remover globais e código de compatibilidade que deixarem de ter consumidores.
7. Atualizar a documentação de arquitetura e testes.

A migração será atômica dentro deste incremento: não haverá páginas usando a
arquitetura antiga depois do commit de implementação.

## Testes

- Usar `node:test`, disponível na biblioteca padrão do Node, sem npm.
- Cobrir construção de URLs, redirecionamento, escape de HTML e normalização de
  imagens com valores literais independentes da implementação.
- Cobrir o cliente HTTP com uma função `fetch` controlada pelo teste, validando
  método, corpo, cabeçalhos, respostas válidas e erros.
- Manter testes HTTP em Python para verificar que todas as páginas e seus módulos
  retornam sucesso pelo servidor do Cinefolio.
- Cobrir o carregamento de um perfil público sem cookie de sessão.
- Executar um smoke test em Node que importe os seis entrypoints com um DOM
  mínimo controlado pelo teste. Esse teste deve detectar erros de sintaxe e de
  resolução do grafo de módulos sem depender de navegador ou biblioteca externa.
- Executar toda a suíte Python existente.

## Critérios de aceite

- Nenhum script de aplicação depende de identificadores globais.
- Todos os imports aparecem no topo dos módulos.
- Cada página possui somente um entrypoint ESM.
- Um visitante sem sessão consegue acessar `profile.html?user=<username>` e os
  dados públicos correspondentes.
- A abertura via `file://` continua exibindo orientação útil.
- O projeto continua sem etapa de build e sem dependências adicionais.
- As seis páginas continuam acessíveis pelo servidor Python.
- Testes JavaScript, testes Python, verificação de sintaxe e smoke test de
  carregamento dos módulos passam.

## Fora do escopo

- Alterar layout, CSS, textos funcionais ou acessibilidade das páginas.
- Modificar endpoints ou contratos da API.
- Decompor os entrypoints em controllers e views menores.
- Adicionar TypeScript, framework frontend ou gerenciador de pacotes.
