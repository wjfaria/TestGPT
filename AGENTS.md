# KAARIVA Reference Agent Instructions

## Purpose
This project provides governed document intake support for public research and regulatory materials. It is not legal, clinical, or regulatory advice.

## Guardrails
- Prioritize governance, traceability, and human review over download volume.
- Do not bypass paywalls or authentication barriers.
- Do not use pirate, shadow-library, or questionable sources.
- Download only from allowlisted domains or manually approved URLs.
- If licensing/access is unclear, route to human review.
- Preserve provenance metadata for every processed seed.

## Coding Guidelines
- Keep components small and auditable.
- Prefer explicit Pydantic schemas and typed functions.
- Keep MVP behavior deterministic and testable.
- Add/maintain pytest coverage for core rules.
