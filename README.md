# Weather Alert Public

Public weather alert dashboard built for Vercel.

This app provides a live nationwide view of active NOAA weather alerts with a focus on `Severe` and `Extreme` conditions. It is designed as a public-facing monitoring dashboard with fast filtering, a state map, and alert cards that make it easy to scan what matters quickly.

## What This App Does

The dashboard helps users:

- View all currently active `Severe` and `Extreme` NOAA alerts
- See which US states are currently affected
- Filter alerts by:
  - location text or state
  - alert type
  - onset status
  - severity
- Use an interactive US map to focus on affected states
- See countdowns for:
  - when upcoming alerts will start
  - when active alerts will expire

## Why This App Exists

The original version of this project was built for an internal operational workflow focused on dispatch risk monitoring for selected ZIP codes.

This public version was redesigned to:

- remove internal network dependencies
- make the dashboard usable by anyone
- keep the experience fast and easy to understand
- support Vercel deployment as a public app
- preserve the useful alert filtering and prioritization logic from the original version

## Core Features

- Nationwide alert dashboard for active NOAA alerts
- Filters for:
  - `Location or State`
  - `Alert Type`
  - `Onset Status`
  - `Severity`
- Interactive US state map
- Clickable affected state list
- Dynamic top metrics that respond to the current filter set
- Countdown timers for upcoming and active alerts
- Manual refresh plus hourly auto-refresh
- Cloud-style back-to-top button

## Data Source

This app uses the NOAA Weather API:

- `https://api.weather.gov/alerts/active`

The app only keeps alerts that match:

- severity: `Severe` or `Extreme`
- status: `Actual`
- not cancelled
- not expired

## How Alert Status Works

Each alert is classified into one of two onset states:

- `ACTIVE`
- `UPCOMING`

Logic:

- if the alert onset/start time is in the future, it is `UPCOMING`
- otherwise it is treated as `ACTIVE`

Card behavior:

- `UPCOMING` alerts show:
  - `Starts in`
  - `Starts At`
- `ACTIVE` alerts show:
  - `Expires in`
  - `Effective`

## Deduplication and Alert Freshness

The app includes logic to avoid showing stale or superseded alerts.

It does this by:

- removing alerts that have been superseded by newer updates
- de-duplicating repeated alert IDs
- keeping only the most relevant current version of an alert

This helps prevent the dashboard from showing old alert versions when NOAA publishes updated records for the same event.

## Filtering Behavior

### Location or State

The text filter supports:

- state code, for example `TX`
- full state name, for example `Texas`
- location text, such as city or area names that appear in NOAA alert coverage text

Important note:

The nationwide dashboard is not a clean city-by-city dataset. It is built from NOAA alert regions and coverage descriptions. That means location filtering matches against NOAA alert text, not a structured nationwide city table.

### Alert Type

Users can filter to a specific NOAA alert event, for example:

- Tornado Warning
- Severe Thunderstorm Warning
- Winter Storm Warning

### Onset Status

Users can filter to:

- `ACTIVE`
- `UPCOMING`

### Severity

Users can toggle between:

- `Extreme`
- `Severe`
- both

Map colors also respond to the severity filter:

- `Extreme` only: red tones
- `Severe` only: orange tones
- both: blue overview scale

## Map Behavior

The US map is a state-level overview.

It shows:

- which states are affected by the currently visible alerts
- how many visible alerts affect each state

Users can:

- hover for full state name and alert count
- click a state to apply that state filter to the dashboard

This is intentionally state-level rather than polygon-level to keep the public app fast, stable, and easy to use.

## Tech Stack

- Static frontend: `index.html`
- Python serverless API on Vercel
- Flask
- Requests
- NOAA Weather API
- Plotly for the US state map
- `uszips.csv` for location lookup support from the original project dataset

## API Routes

- `/api/health`
- `/api/alerts`
- `/api/search`

## Deployment

This app is designed for Vercel deployment.

### Local repo structure

- `index.html`
- `api/`
- `lib/`
- `requirements.txt`
- `vercel.json`
- `uszips.csv`

### Deploy flow

1. Push the repo to GitHub
2. Import the repo into Vercel
3. Vercel builds the Python serverless endpoints automatically
4. The frontend consumes `/api/alerts` and related routes directly

## Limitations

- The nationwide card list is based on NOAA alert coverage regions, not a normalized city-level national table
- Location filtering is text-based for nationwide results
- Browser-displayed times use the viewer's local timezone
- The public app does not yet render NOAA alert polygons

## Future Improvements

- Explicit timezone display options
- Polygon-based alert coverage map
- Smaller optimized location dataset instead of the full ZIP file
- Better mobile card density
- Screenshot-based README documentation
- Saved filter presets
- Alert grouping by event type or state

## Public URL

- `https://weather-alert-public.vercel.app/`
