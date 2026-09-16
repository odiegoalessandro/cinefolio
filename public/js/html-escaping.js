// Mapa de caracteres HTML "perigosos" para suas versões seguras (entidades HTML)
const HTML_ENTITIES = Object.freeze({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
});

// Esta função é a principal defesa do frontend contra XSS (Cross-Site
// Scripting): sempre que um dado vindo do usuário (bio, review, nome
// exibido, etc) é inserido no HTML via innerHTML, ele PRECISA passar por
// aqui primeiro. Sem isso, alguém poderia colocar "<script>" numa bio e
// executar código malicioso na tela de quem visualiza o perfil.
export function escapeHtml(value) {
  if (value === null || value === undefined) {
    return '';
  }

  // Troca cada caractere perigoso pela sua entidade HTML equivalente
  // (ex: "<" vira "&lt;"), fazendo o navegador exibir o caractere como
  // TEXTO em vez de interpretá-lo como parte da estrutura HTML  
  return String(value).replace(
    /[&<>'"]/g,
    (character) => HTML_ENTITIES[character]
  );
}
