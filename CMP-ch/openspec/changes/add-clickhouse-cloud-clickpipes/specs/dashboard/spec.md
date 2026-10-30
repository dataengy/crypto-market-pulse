## ADDED Requirements

### Requirement: Hosted dashboard
The same dashboard app SHALL deploy to Streamlit Community Cloud as a private app. It SHALL read the platform secrets into the strict loader, connect as `cmp_dash`, and commit no secrets to the repo.

#### Scenario: Live bars in the hosted app
- **WHEN** the main ClickPipe is Running and the producer has published within `dashboard.stale_after_s`
- **THEN** the hosted app shows current 1m bars without a stale badge

#### Scenario: Missing platform secret
- **WHEN** `CLICKHOUSE_DASH_PASSWORD` is not set in the app's secrets
- **THEN** the app shows an error naming that key, and does not fall back to any other user
