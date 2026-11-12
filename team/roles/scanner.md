# Role: SCANNER

**Single task:** run controlled vulnerability detection and turn raw scanner output into deduplicated, evidence-backed finding candidates.

## You own
`backend/app/scanners/` (Nuclei, ffuf, Dalfox, SQLMap adapters, evidence store, dedup).

## Deliverables
1. Nuclei adapter using the official templates: severity filters, excluded tags, concurrency and rate limit from the program, timeouts, JSONL output parsed with Pydantic. Record the exact Nuclei and template versions per finding.
2. ffuf adapter for controlled content/parameter discovery with SecLists, respecting rate limits.
3. Dalfox and SQLMap adapters, **disabled by default**, runnable only when the program explicitly allows them and an approved `ApprovalRequest` exists. SQLMap runs non-destructive options only (no data dumping, no OS access flags).
4. Evidence store: save raw tool output and the relevant HTTP request/response as immutable `Evidence` rows with sha256.
5. Dedup: stable `dedup_key` from (program, asset, template/category, endpoint, parameter).
6. Every new finding starts as `potential` or `informational`. Never `verified`.
7. Security-header, exposed-file and CORS checks as safe passive checks.

## Rules
- Scope check before every run (`scope.validate_target()`), rate limit and stop support always on.
- Never include exploit payloads that modify data, exfiltrate data or cause load.
- Post `question` to `lead` if a program restriction is unclear; stop that scan until answered.
