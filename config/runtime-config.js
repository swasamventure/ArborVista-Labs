(function () {
  const host = window.location.hostname;
  const local = host === 'localhost' || host === '127.0.0.1' || host === '';
  const injected = window.ARBOR_VISTA_ENV || {};
  window.ARBOR_VISTA_CONFIG = Object.freeze({
    apiBaseUrl: String(injected.apiBaseUrl || (local ? '/api/v1' : 'https://api.swasamventure.com/v1')).replace(/\/$/, ''),
    propertySlug: injected.propertySlug || 'arbor-vista-retreat',
    environment: injected.environment || (local ? 'development' : 'production'),
    requestTimeoutMs: Number(injected.requestTimeoutMs || 15000),
    stripeEnabled: false,
    outboundEmailEnabled: false
  });
})();
