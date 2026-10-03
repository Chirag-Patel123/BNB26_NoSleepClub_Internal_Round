# Drop-in for web/

Unzip at the repo root (the zip already contains the `web/` folder), then:

    cd web && npm install && npm run dev

Replaced/added: index.html, vite.config.js, src/{main.jsx,App.jsx,pages.jsx,Graph.jsx,ui.jsx,api.js,data.js,styles.css}
Not touched: package.json, package-lock.json, .gitignore, .oxlintrc.json, README.md
(only react + react-dom are needed, which your package.json already has)

Safe to delete afterwards (no longer imported): src/App.css, src/index.css, src/assets/

API: set VITE_API_URL=/api in web/.env. Backend routes must live under /api
(app.include_router(router, prefix="/api")). Map responses onto the run shape in src/data.js inside src/api.js.
Production: npm run build, then serve web/dist with StaticFiles mounted last.
