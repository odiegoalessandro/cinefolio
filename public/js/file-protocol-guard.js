// Este script roda ANTES de tudo (é carregado como o primeiro <script> em
// cada página HTML, sem "type=module") e existe para evitar uma confusão
// comum: o usuário abrindo o arquivo .html diretamente no navegador
// (duplo clique) em vez de acessar via http://127.0.0.1:8000.

(() => {
  // window.location.protocol é "file:" quando a página foi aberta como um
  // arquivo local, e não através de um servidor HTTP real
  if (window.location.protocol !== 'file:') {
    return; // tudo certo: a página está sendo servida via HTTP, segue normalmente
  }

  // Espera o HTML carregar completamente antes de substituir o conteúdo
  document.addEventListener('DOMContentLoaded', () => {
    // Substitui TODO o corpo da página por uma mensagem de aviso,
    // explicando como rodar o projeto corretamente
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
