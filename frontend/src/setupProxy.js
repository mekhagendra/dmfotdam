const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  // Required for Google Sign-In popup/iframe communication
  app.use((req, res, next) => {
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin-allow-popups');
    next();
  });

  // Proxy REST API calls to the FastAPI backend
  const apiProxy = createProxyMiddleware({
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: false, // Handled manually below to avoid intercepting webpack HMR (/ws)
    onError: (err, req, res) => {
      console.error('Proxy error:', err);
      if (res && !res.headersSent) {
        res.writeHead(502, { 'Content-Type': 'text/plain' });
        res.end('Bad Gateway');
      }
    },
  });

  app.use('/api', apiProxy);

  // Only proxy WebSocket upgrades for /api/* paths.
  // This prevents webpack HMR (/ws) from being forwarded to the backend.
  app.on('upgrade', (req, socket, head) => {
    if (req.url && req.url.startsWith('/api')) {
      apiProxy.upgrade(req, socket, head);
    }
  });
};
