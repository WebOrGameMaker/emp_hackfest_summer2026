# HazardMap

**Human-AI report system for safety data**

A public safety map constructed on the idea that the hard part of crowdsourced hazard
reporting is not collecting reports, but it is deciding which reports describe the
same real-world thing. HazardMap normalizes messy human input, such as a photo or a
sentence, into a structured record. Then, it aggregates records that
describe one event into a single marker with a confidence score.

Twelve people reporting one fallen tree should produce one hazard at high
confidence, not twelve different pins.

---

## How to Run

```bash
./run.sh
```

Then open [http://localhost:8000](http://localhost:8000).

The script creates a virtualenv, installs pinned dependencies, seeds the demo
database if it is empty, and serves the app. Nothing else is required: no
Node.js, no build step, no map API key, no AI key.

Requires Python 3.9 or newer. Dependencies are pinned to the last releases that
still support 3.9.

### Optional: run against a real model

```bash
cp .env.example .env
# set HAZARDMAP_AI_KEY=sk-...
./run.sh
```

With no key the app runs its deterministic demo analyzer. With a key it calls
an OpenAI-compatible chat completions endpoint with a JSON-schema-constrained
response. Clustering, scoring, storage, and the UI are identical either way.
The seam is `backend/ai/base.py::HazardAnalyzer`.

---



## How it works

```
citizen observation ──> AI normalization ──> structured hazard record
                                                      │
                                                      ▼
                                          spatial + temporal clustering
                                                      │
                                                      ▼
                                       log-odds confidence  ──> live map
```

A new report joins an existing hazard when the normalized category matches, the
distance is inside that category's radius, and the hazard was last confirmed
inside its time window (spatial + temporal clustering). Otherwise it opens a new hazard.

Evidence accumulates in log-odds. A single report is capped near 72% and
nothing ever exceeds 97% (logically, one report always needs to be taken with a grain of
salt. Similarly, multiple reports don't mean that something is 100% certain). 
The interface says "corroborated", never "verified," for this reason.

The in-app **How it works** tab has the per-category thresholds, the confidence
breakdown, and the system's limits.

---



## Layout

```
backend/
  main.py            FastAPI app: REST routes, SSE stream, static mount
  taxonomy.py        the 8 categories: icons, lexicon, radii, time windows
  models.py          Pydantic schemas shared by the AI layer, logic and API
  clustering.py      haversine, merge evaluation, centroid — pure functions
  confidence.py      log-odds scoring with the returned breakdown
  db.py              SQLite schema, thread-local connections, report pipeline
  seed.py            demo data
  places.py          offline reverse geocoding for demo landmarks
  ai/
    base.py            the HazardAnalyzer protocol
    demo.py            deterministic offline analyzer
    openai_provider.py real implementation, used when a key is present
    factory.py         picks one based on the key
frontend/            no build step; ES modules, vendored Leaflet
scripts/
  check_demo_flow.py exercises submit-and-merge without a browser
```

```bash
python -m scripts.check_demo_flow
```

API: `GET /api/meta`, `/api/hazards`, `/api/hazards/{id}`, `/api/scenarios`,
`/api/reports/{id}/photo`, `/api/stream`, `/healthz`;
`POST /api/analyze`, `/api/reports`, `/api/demo/reset`.

---



## Known limits

Deliberately out of scope: authentication, user accounts (login system), moderation, live
traffic and weather feeds, and any build tooling.

Photos are base64 in SQLite. Fine for a prototype, not for production.

HazardMap is decision support and awareness. It is not a dispatch system and
must not replace emergency services. It has no ability to report emergencies as of current.