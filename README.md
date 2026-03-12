# Weather Alert Public

Public weather alert dashboard prepared for Vercel.

## Features

- Nationwide dashboard for active `Severe` and `Extreme` alerts
- City and state search
- Manual refresh
- Hourly auto-refresh on the client
- No client-side secret exposure

## Stack

- Static `index.html`
- Flask serverless API in `api/*.py`
- NOAA alerts API
- `uszips.csv` for city/state lookup

## Routes

- `/api/alerts`: nationwide active alert snapshot
- `/api/search?city=Seattle&state=WA`: city/state severe/extreme lookup
- `/api/health`: simple health check

## Deploy

Import this folder as a Vercel project.
