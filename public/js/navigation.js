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
