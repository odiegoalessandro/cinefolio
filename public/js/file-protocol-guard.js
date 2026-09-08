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
