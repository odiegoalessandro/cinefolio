// createPageUrl monta a URL final de uma página, incluindo parâmetros de
// busca (querystring), de forma consistente em todo o app
export function createPageUrl(
  pageName,
  params = {},
  baseUrl = globalThis.location.href  // por padrão, usa a URL atual como referência
) {
  // O construtor URL(caminho relativo, base) resolve o caminho final
  // corretamente, mesmo que a página atual esteja em subpastas diferentes
  const url = new URL(pageName, baseUrl);

  // Adiciona cada parâmetro como query string (?chave=valor), ignorando
  // valores undefined/null (que significam "sem esse parâmetro")  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });

  return url.href;
}

// navigateTo efetivamente MUDA a página do navegador para a URL montada
export function navigateTo(
  pageName,
  params = {},
  locationRef = globalThis.location   // permite injetar um "location" falso em testes
) {
  locationRef.href = createPageUrl(pageName, params, locationRef.href);
}
