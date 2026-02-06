#!/bin/sh
set -e
# Inject runtime env into config.js so the app can read it without a rebuild
cat > /app/dist/config.js << EOF
window.__API_BASE_URL__ = "${VITE_API_URL:-http://localhost:4000}";
window.__APP_URL__ = "${VITE_APP_URL:-http://localhost:3000}";
EOF
exec serve -s dist -l 3000
