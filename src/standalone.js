// Minimal stand-in for the dashboard runtime the page was written against:
// datasets embedded in the page, calcs run once, params kept in localStorage.
window.dash = (() => {
  const DEFAULT_PARAMS = { period: '10y', nation: 'all', list: 'area', metric: 'sun', picks: ['E06000043', 'E08000003', 'S12000049', 'E06000052-4'] };
  const STORE_KEY = 'uk-climate-compare:params';
  const colors = ['#d9622b', '#2f7fbf', '#3e9b5f', '#9b59b6', '#c9a227', '#d0457c'];

  const sources = {};
  for (const el of document.querySelectorAll('script[data-dataset]')) {
    const text = el.textContent;
    sources[el.dataset.dataset] = { status: 'ok', data: el.type === 'application/json' ? JSON.parse(text) : d3.csvParse(text) };
  }

  let params = { ...DEFAULT_PARAMS };
  try { Object.assign(params, JSON.parse(localStorage.getItem(STORE_KEY) || '{}')); } catch { /* storage unavailable */ }

  const listeners = [];
  let pending = false;
  const notify = () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; for (const fn of listeners) fn(); });
  };

  let lastWidth = window.innerWidth;
  window.addEventListener('resize', () => {
    if (window.innerWidth === lastWidth) return; // ignore mobile toolbar height changes
    lastWidth = window.innerWidth;
    notify();
  });

  return {
    colors,
    calc(name, spec) {
      sources[name] = { status: 'ok', data: spec.fn(...spec.inputs.map((i) => sources[i].data)) };
    },
    data: (name) => sources[name] || { status: 'loading' },
    params: () => params,
    setParams(patch) {
      params = { ...params, ...patch };
      try { localStorage.setItem(STORE_KEY, JSON.stringify(params)); } catch { /* storage unavailable */ }
      notify();
    },
    onData(fn) { listeners.push(fn); notify(); },
  };
})();
