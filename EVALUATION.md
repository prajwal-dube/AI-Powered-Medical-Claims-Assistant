# Medical Claims Assistant Evaluation

Date: 2026-10-16
Environment: Windows 11, Docker Desktop 4.91.0, Python 3.11, local workspace
Scope: Synthetic-data-only medical claims project; local extractor and deterministic rules only; no remote LLM provider or cloud deployment configured.

## Evidence table

| Command | Environment | Date | Exact output / result | Limitations |
| --- | --- | --- | --- | --- |
| `docker version` + `docker compose up --build -d` + `docker compose ps` | Local Docker Desktop (desktop-linux context) | 2026-10-16 | Docker server reported `Docker Desktop 4.91.0 (239619)`. Containers started successfully: `medical-claims-assistant-api-1` `Up (healthy)` on `0.0.0.0:8000->8000/tcp`; `medical-claims-assistant-dashboard-1` `Up` on `0.0.0.0:8501->8501/tcp`. | Verified local container startup only; no cloud deployment or live remote LLM. |
| `curl.exe -sS http://localhost:8000/health` | Local API container | 2026-10-16 | `{"status":"ok"}` | Health check passed locally only. |
| `curl.exe -sS -o NUL -w "HTTP %{http_code}\n" http://localhost:8000/docs` | Local API container | 2026-10-16 | `HTTP 200` | Verified local docs endpoint only. |
| `curl.exe -sS -o NUL -w "HTTP %{http_code} - Content-Type: %{content_type}\n" http://localhost:8501` | Local dashboard container | 2026-10-16 | `HTTP 200 - Content-Type: text/html; charset=utf-8` | Verified local dashboard page only. |
| `python -m venv .venv` + `.\.venv\Scripts\Activate.ps1` + `python -m pip install -q -e '.[test]'` + `pytest -q` | Local venv on host machine | 2026-10-16 | `4 passed, 1 warning in 2.76s` | Warning from `starlette.testclient`/`httpx` deprecation only; no production issues observed in synthetic tests. |
| `python scripts/benchmark.py --output benchmark_results.json` | Local venv on host machine | 2026-10-16 | `field_values_correct: 180/180`, `documents_with_exact_flags: 30/30`, `median_processing_ms: 0.058`, `p95_processing_ms: 0.164`, `scope: local extraction and rules only; excludes API, I/O, LLM, and deployment` | Synthetic benchmark only; not a real-world patient dataset or general model accuracy metric. |
| `curl.exe -sS -w "\n__STATUS__:%{http_code}" -F "file=@samples/claim_001.txt" http://localhost:8000/claims` (first submission) | Local API container | 2026-10-16 | Response included `flags:[]` and `__STATUS__:201` | Initial upload succeeded; duplicate logic not active yet. |
| second `curl.exe -sS -w "\n__STATUS__:%{http_code}" -F "file=@samples/claim_001.txt" http://localhost:8000/claims` | Local API container | 2026-10-16 | Response contained `"code":"possible_duplicate"` and `__STATUS__:201` | Verified duplicate detection on same document repeated. |
| `curl.exe -sS -F "file=@samples/claim_002_missing.txt" http://localhost:8000/claims` | Local API container | 2026-10-16 | Response contained `"code":"missing_procedure"` and `__STATUS__:201` | Verified missing procedure detection. |
| `curl.exe -sS http://localhost:8000/stats` | Local API container | 2026-10-16 | `{"total_in_window":3,"flagged_in_window":2,"flag_counts":{"missing_procedure":1,"possible_duplicate":1},"window_limit":500}` | Verified local dashboard count summary only. |
| `docker compose logs --no-color --tail=80 api` + `docker compose logs --no-color --tail=40 dashboard` | Local Docker Desktop | 2026-10-16 | API logs showed `POST /claims HTTP/1.1` 201 Created and `GET /stats HTTP/1.1` 200 OK; dashboard logs showed Streamlit started at `http://localhost:8501` | No failures observed in the exercised flow; logs confirm healthy service behavior. |

## Summary of what succeeded

- Docker Desktop is running and the project starts successfully with Docker Compose.
- The API health endpoint, Swagger docs, and dashboard all responded with HTTP 200.
- The local test suite passed: `4 passed`.
- The local synthetic benchmark passed with exact field matching `180/180` and exact flag-set matching `30/30` on the generated labeled fixtures.
- Duplicate detection was verified with the same sample file submitted twice: the second response contained `possible_duplicate`.
- Missing-procedure detection was verified on `claim_002_missing.txt`.
- Dashboard counts matched observed local data: `total_in_window=3`, `flagged_in_window=2`.

## What is blocked / not verified

- No provider key or cloud account access was configured, so no remote LLM evaluation or live cloud deployment was attempted.
- The project is scoped to synthetic docs only; no real patient data or production HIPAA-governed environment was used.
- The benchmark is explicitly limited to the generated labeled fixtures and local extractor + rules only; it does not claim general model accuracy.

## Recommendation

This project is strong for a portfolio case study and interview discussion around AI document processing, API development, validation, and local deployment. It is not a production clinical or insurance adjudication system and should be framed that way in resumes and interviews.
