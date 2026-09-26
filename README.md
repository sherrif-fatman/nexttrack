# NextTrack

NextTrack is a session-based music recommendation web application developed as a final-year university project. It explores whether useful and diverse music recommendations can be generated from temporary session context without relying on a persistent behavioural user profile.

The project investigates the research question:

> **To what extent can a music recommender provide relevant and diverse recommendations using temporary session context without relying on persistent user profiling?**

Users build a temporary listening context by selecting tracks from the catalogue. NextTrack compares candidate tracks with the selected session tracks and generates recommendations using musical and artist-related similarity features. Optional refinement controls allow the user to adjust the style, tempo and intensity of the recommendations.

## Architecture

NextTrack uses a separate frontend, backend and database:

- **Frontend:** Next.js 16.2.6, React 19.2.4 and TypeScript
- **Backend:** Django 5.1.1 and Django REST Framework 3.15.2
- **Database:** PostgreSQL 17
- **Containerisation:** Docker and Docker Compose
- **Production application server:** Gunicorn
- **Music data:** Million Song Dataset
- **Metadata enrichment:** MusicBrainz and Cover Art Archive
- **Supplementary playback:** Spotify Web API / Web Playback SDK

The main backend API provides endpoints for catalogue search, recommendation generation and evaluation feedback.

## Recommendation Approach

Recommendations are generated from the tracks selected during the current session rather than from a persistent listening-history profile.

The final similarity weighting is:

- artist terms: 0.50
- tempo: 0.20
- loudness: 0.20
- key and mode: 0.10

Artist-term similarity uses weighted Jaccard similarity. When several tracks are selected, a candidate is compared with each selected track and the component similarities are averaged.

The recommender excludes tracks already selected in the session and candidates by the same artist. Optional style, tempo and intensity refinements apply secondary scoring adjustments to the base similarity score.

## Project Structure

```text
nexttrack_app/
├── backend/
│   ├── config/                 # Django project configuration
│   ├── evaluation_data/        # De-identified evaluation inputs and derived results
│   └── recommendations/
│       ├── management/         # Catalogue, enrichment and evaluation commands
│       ├── migrations/
│       ├── services/           # Recommendation and similarity logic
│       └── tests/              # Automated backend tests
├── frontend/
│   ├── app/                    # Next.js application
│   ├── components/             # React UI components
│   ├── lib/                    # Spotify and supporting client utilities
│   └── public/
├── docker-compose.yml
└── docker-compose.production.yml
```

## Prerequisites

For the Docker-based development setup:

- Docker with Docker Compose
- Node.js 20 and npm for running the frontend locally
- Million Song Dataset files if rebuilding or enriching the catalogue
- A Spotify developer application if testing Spotify playback

The supplied frontend Docker image also uses Node.js 20.

## Environment Configuration

Real environment files are intentionally excluded from version control. Example files are provided as templates.

Create the backend development environment file:

```bash
cp .env.example .env
```

The backend configuration includes:

```text
DEBUG
SECRET_KEY
DJANGO_ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
BACKEND_PORT
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
```

Create the frontend local environment file:

```bash
cp frontend/.env.example frontend/.env.local
```

Frontend configuration uses:

```text
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_SPOTIFY_CLIENT_ID
NEXT_PUBLIC_SPOTIFY_REDIRECT_URI
```

Replace placeholder values with appropriate local configuration. Do not commit credentials or production secrets.

## Local Development

Start PostgreSQL and the Django backend from the project root:

```bash
docker compose up --build
```

The development backend container runs Django on port 8000 internally. The host port is controlled by `BACKEND_PORT` in `.env`.

The development Compose file contains a host volume mapping for the Million Song Dataset HDF5 subset. Change the host side of this mapping in `docker-compose.yml` to the location of the dataset on your own machine if catalogue enrichment is required.

In another terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

The frontend is normally available at `http://localhost:3000`.

Apply Django migrations when setting up a new database:

```bash
docker compose exec backend python manage.py migrate
```

## Catalogue Preparation

Million Song Dataset source files are deliberately not stored in this repository.

The catalogue tooling uses:

- `track_metadata.db` for track metadata
- `artist_term.db` for artist terms
- the Million Song Dataset HDF5 subset for additional track and artist-term information

The main preparation workflow is:

1. `extract_msd_metadata` — imports MSD metadata into the `ImportedTrackData` staging table.
2. `enrich_staging_genres` — enriches staged records using artist terms.
3. `process_staged_tracks` — converts staged records into the cleaned NextTrack catalogue.
4. `enrich_tracks_from_msd` — enriches catalogue tracks from the HDF5 subset.

Additional management commands support MusicBrainz matching and Cover Art Archive artwork enrichment.

For command-specific options, use Django's built-in help, for example:

```bash
docker compose exec backend python manage.py extract_msd_metadata --help
```

The development Compose configuration mounts the HDF5 subset at `/data/msd` inside the backend container. The SQLite metadata databases may be supplied explicitly to their respective commands or placed in the expected ignored external-data directory.

## Tests

Run the backend automated test suite with:

```bash
docker compose exec backend python manage.py test recommendations.tests
```

Build the frontend with:

```bash
cd frontend
npm run build
```

The frontend also provides an ESLint script:

```bash
npm run lint
```

## Evaluation and Reproducibility

The repository includes the offline recommender evaluation command:

```text
backend/recommendations/management/commands/evaluate_recommender.py
```

It reproduces the weighting sensitivity analysis used in the project evaluation. The analysis compares the final weighting with equal-weight and leave-one-component-out configurations.

This is a sensitivity analysis of recommendation behaviour rather than evidence that one weighting configuration provides higher recommendation quality.

The `backend/evaluation_data/` directory contains frozen, de-identified session-context data and derived offline evaluation outputs used for reproducibility. It does not contain participant names, email addresses or other direct identifiers.

The evaluation command is intended to run inside the backend container and uses `/app/evaluation_data` for its evaluation files.

## Privacy Model

NextTrack is designed around temporary session context rather than persistent behavioural user profiling.

Recommendation generation uses the tracks selected in the current NextTrack session together with any request-time refinement settings. Evaluation feedback does not feed back into recommendation ranking.

Application session and evaluation records may persist in the database for system operation and research evaluation, so the system should not be described as technically stateless. The privacy distinction is that recommendation generation does not depend on a persistent behavioural profile of the listener.

Spotify integration is supplementary and is used for authorised playback. NextTrack does not use a listener's Spotify listening history as an input to recommendation ranking.

## Production Deployment

The repository includes `docker-compose.production.yml` for the deployed architecture.

Production uses:

- PostgreSQL 17
- Django served through Gunicorn
- Next.js running as a separate frontend service
- backend and frontend services bound to localhost for use behind the production web server / reverse proxy
- separate production environment files that are not committed to Git

The production Compose configuration is separate from the local development configuration so that development-specific dataset mounts and Django's development server are not used in deployment.

## External Data and Services

NextTrack makes use of the following external resources:

- **Million Song Dataset** — catalogue and audio-derived metadata
- **MusicBrainz** — album and release metadata enrichment
- **Cover Art Archive** — album artwork enrichment
- **Spotify** — supplementary authorised playback

External datasets and service credentials are not included in the repository. Use of these resources remains subject to their respective terms and availability.

## Research Context

NextTrack was developed as an academic project investigating session-based recommendation, recommendation diversity and privacy-conscious personalisation. The application and accompanying evaluation are intended as a research prototype rather than a commercial music recommendation service.
