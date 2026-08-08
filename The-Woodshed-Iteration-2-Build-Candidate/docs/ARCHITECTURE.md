# Architecture — Iteration 2 Build Candidate

Runtime direction:

`Browser -> Nginx gateway -> Next.js / FastAPI -> services -> domain -> integrations / canonical persistence`

FastAPI lifespan owns the cache, database wrapper, one pooled Sleeper `httpx.AsyncClient`, one Sleeper concurrency semaphore, Redis-capable rate limiter and bounded Guillotine simulation semaphore.

Data direction:
1. provider payload;
2. provider adapter validation;
3. provider-neutral schema (`app/schemas/canonical.py`);
4. canonical persistence models (`app/data/models.py`);
5. league context / decision input;
6. domain output;
7. eventual ModelRun/DataLineage/Recommendation persistence.

The final persistence step is **not yet universally wired** for every decision route and is documented as remaining work.

Projection contracts are explicit: `raw_stats` is scored by Woodshed; `fantasy_points` must carry a compatible scoring fingerprint. Unsupported historical ADP/team-at-event and unavailable live projection/market sources are not invented.
