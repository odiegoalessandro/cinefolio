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
