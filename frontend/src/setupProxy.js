const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  // Required for Google Sign-In popup/iframe communication
  app.use((req, res, next) => {
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin-allow-popups');
    next();
  });

  // Proxy REST API calls to the FastAPI backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      // Do NOT set ws:true here — it hijacks the dev server's own /ws hot-reload socket
    })
  );

  // Proxy only the app's WebSocket path to the backend
  app.use(
    '/api/v1/ws',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      ws: true,
    })
  );
};
