# Kenya Investment Intelligence — Dashboard

## Deployment status

- Public dashboard: https://kenya-investment-intelligence.vercel.app
- Hosting: Vercel
- Build status: successful
- Data service: official public National Treasury/PDMO JSON feeds connected as a fallback
- Market coverage: domestic and external debt stocks, debt service and annual macroeconomic indicators
- Market gaps: NSE share prices and secondary-market bond yields still require separate approved sources

The current Vercel deployment was created from a dashboard-only source snapshot. The Vercel GitHub integration has not yet been connected to this repository, so new commits do not automatically trigger deployments yet. The feature branch must be deployed after its checks pass.

A Next.js 16 dashboard for Kenyan equities, fixed income, macroeconomic research and risk analysis.

## Design direction

A restrained gold-and-ink visual system with warm neutral surfaces, readable data tables and quiet motion. The interface is designed to feel like a working research terminal rather than a promotional landing page. It intentionally does not seed itself with invented market values.

## Runtime and dependencies

The dashboard uses Next.js 16, React 19, Motion and Recharts 3. CI runs on Node.js 22, and the deployment requires Node.js 20.9 or newer.

## Run locally

```powershell
cd dashboard
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Data connection

Set `DATA_API_URL` and `DATA_API_TOKEN` as server-side Vercel environment variables to use the read-only FastAPI service in `../ingestion_service`. The browser never connects directly to PostgreSQL. When the authorised service is unavailable or not configured, the dashboard falls back to public PDMO JSON datasets, preserving the original reporting period, units and source links. If a source is unavailable, it is labelled unavailable rather than replaced with fabricated figures.

## Deploy to Vercel

Create a Vercel project from this GitHub repository and set the Root Directory to `dashboard`. Add `DATA_API_URL` as a server-side environment variable. Do not add database credentials or importer tokens to `NEXT_PUBLIC_*` variables.

## Notes

- The original Streamlit research application remains in `website/`.
- The research calculations and source data are not copied into the public frontend.
- The PDMO adapter retrieves official JSON downloads from the National Treasury and displays source attribution and original-source links. Wider reuse remains subject to the source owner’s terms; the availability of a download does not itself grant unrestricted redistribution rights.
- Rock Data Plus remains disconnected pending Rock Investment Bank’s written permission and agreed access terms.
- Public deployment must only expose datasets that are approved for display and redistribution.
- Review the draft Terms and Privacy pages and complete their operating details before public launch.

## Install on a phone

The dashboard is configured as an installable Progressive Web App (PWA).

- **Android (Chrome):** open the dashboard, tap the Install control, or use the browser menu → Install app / Add to Home screen.
- **iPhone (Safari):** open the dashboard, tap Share → Add to Home Screen.
- Once installed, it opens in its own app-style window. The service worker supplies a simple offline screen; market API responses are deliberately not cached.

The PWA needs HTTPS, a valid manifest and the icons in `public/icons/`. Vercel serves the site over HTTPS.
