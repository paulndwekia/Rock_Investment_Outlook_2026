# Kenya Investment Intelligence — Dashboard

A Next.js dashboard for Kenyan equities, fixed income, macroeconomic research and risk analysis.

## Design direction

A restrained gold-and-ink visual system with warm neutral surfaces, readable data tables and quiet motion. The interface is designed to feel like a working research terminal rather than a promotional landing page. It intentionally does not seed itself with invented market values.

## Run locally

```powershell
cd dashboard
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Data connection

Set `DATA_API_URL` to the read-only FastAPI service in `../ingestion_service`. The browser never connects directly to PostgreSQL. If the service is not configured, the dashboard displays a clear empty state rather than sample or fabricated figures.

## Deploy to Vercel

Create a Vercel project from this GitHub repository and set the Root Directory to `dashboard`. Add `DATA_API_URL` as a server-side environment variable. Do not add database credentials or importer tokens to `NEXT_PUBLIC_*` variables.

## Notes

- The original Streamlit research application remains in `website/`.
- The research calculations and source data are not copied into the public frontend.
- Public deployment must only expose datasets that are approved for display and redistribution.
- Review the draft Terms and Privacy pages and complete their operating details before public launch.
