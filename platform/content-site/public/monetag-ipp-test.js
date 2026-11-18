(() => {
  const host = 'content.shopnoltd.dpdns.org';
  const path = location.pathname.replace(/\/+$/, '');
  if (location.hostname !== host) return;
  if (!/^\/blog\/[^/]+$/.test(path)) return;
  if (new URLSearchParams(location.search).get('monetag-test') !== '1') return;

  const root = document.querySelector('#content');
  if (!root) return;

  let loaded = false;
  const loadForPublishedArticle = () => {
    if (loaded || !root.querySelector('.article')) return;
    loaded = true;
    const script = document.createElement('script');
    script.dataset.zone = '12129960';
    script.setAttribute('data-cfasync', 'false');
    script.src = 'https://nap5k.com/tag.min.js';
    script.async = true;
    script.onerror = () => console.warn('Monetag IPP test loader failed');
    document.head.append(script);
  };

  const observer = new MutationObserver(() => {
    if (root.querySelector('.article')) {
      observer.disconnect();
      loadForPublishedArticle();
    }
  });
  observer.observe(root, { childList: true, subtree: true });
  loadForPublishedArticle();
})();
