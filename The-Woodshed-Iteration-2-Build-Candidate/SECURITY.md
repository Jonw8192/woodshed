# Security, Privacy, and Threat Model — Build Candidate

## Trust boundaries
Browser → gateway → Next.js / FastAPI → Redis / PostgreSQL / Sleeper / optional AI provider.

## Implemented controls
- Pydantic request validation and bounded simulation/list sizes.
- Only the Nginx gateway publishes a host port in supplied Compose.
- Gateway 1 MB request-body cap plus application Content-Length guard.
- Trusted proxy CIDR checks before honoring `X-Forwarded-For`.
- Request IDs and response security headers.
- Redis-backed rate-limiter path; Redis failure is fail-closed when that path is configured.
- Shared pooled Sleeper HTTP client, per-process provider semaphore, bounded timeout/retry, typed provider errors, cache coalescing and managed key-lock cleanup.
- Non-root API/web images, dropped capabilities/read-only filesystems where configured.
- Environment startup validation for required DB/Redis and AI configuration combinations.
- Build-candidate account-key authentication primitive for protected durable import; account-scoped league uniqueness.
- AI disabled by default.
- Secrets are environment configuration and are excluded from the archive.

## Not yet release-verified / incomplete
- Managed user identity/session UX and comprehensive object-level authorization suite.
- Atomic daily/monthly AI quotas, spend ceilings, claim-level evidence validation and model-cost telemetry.
- Real Redis multi-process rate-limit test.
- Postgres authorization/cross-tenant integration tests.
- Chunked-body streaming limit inside FastAPI; gateway is intended as the only public path.
- Dependency/SAST/secret/container scans in a clean verification environment.
- Browser CSRF/session analysis after managed browser auth is selected.
- External penetration/abuse testing.

## Privacy/data handling
Do not log credentials, account keys, provider tokens, AI keys, full private prompts or unnecessary personal data. User-linked league state must be authorization-scoped. Recommendation persistence should keep normalized facts, lineage IDs and hashes rather than secret-bearing source payloads.

## Release policy
This archive is **NOT READY**. AI must remain disabled publicly until its governance gate is complete. See `EXTERNAL_VERIFICATION_QUEUE.md` for security verification commands.
