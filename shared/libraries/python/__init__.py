"""Placeholder for shared Python utilities across shopnoltd services.

Every platform/*/Dockerfile does `COPY shared/libraries/python /app/shared`,
but no service currently imports anything from it (verified: no
`from shared` / `import shared` in any service's app code). This stub only
exists so `docker compose build` doesn't fail on a missing COPY source.

If/when you actually build shared logging, auth helpers, etc. meant to be
reused across services, put it here.
"""
