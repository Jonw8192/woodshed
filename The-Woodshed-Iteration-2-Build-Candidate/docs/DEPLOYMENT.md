# Deployment — Candidate Only

The provided topology intends Nginx on port 8080 as the only public host exposure. API/web services are internal Compose services.

A deployment-ready claim is **not** made because the current environment cannot generate/verify the frontend lock, Docker images, Postgres/Redis runtime, browser suite or staging deployment.

Verified settings names are defined in `backend/app/core/config.py` and mirrored in `backend/.env.example`.

See `EXTERNAL_VERIFICATION_QUEUE.md` for exact build, migration, Compose, scan, backup/restore and deployment verification steps.
