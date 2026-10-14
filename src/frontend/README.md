# iManage AI Workspace frontend

React 18 + TypeScript + Vite single-page app for the App Service UI. The SPA calls only the same-origin proxy API documented in [`../../docs/api-contract.md`](../../docs/api-contract.md) under `/api`.

## Package feed

Use Node.js 22.12+ and the public npm registry configured in `.npmrc`:

```ini
registry=https://registry.npmjs.org/
```

Run installs from this folder:

```powershell
cd src\frontend
npm ci
```

If your organization requires a package mirror, configure it locally rather than committing
organization-specific registry URLs or credentials.

## Development

```powershell
npm run dev
```

Vite serves the SPA locally and proxies `/api` to `http://localhost:8000` for the backend proxy.

## Build

```powershell
npm run build
```

Production builds emit `dist/` and use `base: '/ui/'` because App Service serves the bundle under `/ui/`.
