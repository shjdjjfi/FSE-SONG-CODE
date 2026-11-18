# N22 experimental report — 18 November 2026

**Study:** *Checking Data Contracts Across Converging Database Migration Paths*

**Honest maturity:** public-case, reproducible **exploratory replication** with
two distinct public defect mechanisms. **Not yet a complete FSE Industry
evaluation.** All numbers below were produced by the code and SQLite databases
in this branch; no industrial event logs or human subjects are implied.

## Research question and definitions

We define two executed paths as **structurally convergent** only if they
finish successfully, produce the same SQLite object definitions (excluding
SQLite's internal objects), and reach the same logical migration ledger
(excluding timestamps/sequence auto-ids). The semantic question is whether
required application records and relationships nevertheless differ.

The comparison uses 1) schema/ledger, 2) table cardinality, 3) raw snapshot
comparison, and 4) an explicit business-data contract. Business contracts
were authored using public issue reproductions and documented application
data expectations; they are **not automatically discovered** or learned.

Reference data come from separately executed, controlled repair paths:
one in-memory Open WebUI patch following a public issue and one Drizzle ORM
workaround that disables SQLite foreign keys *before* migration begins.
Neither reference is represented as a released upstream fix.

## Input provenance, execution, and independently visible symptom

| Source | Frozen input and real execution | Real-world issue evidence | Status of our application observation |
| --- | --- | --- | --- |
| Open WebUI | v0.9.6, SHA 1a97751e, unchanged `b10670c03dd5` Alembic body on SQLite; SQLAlchemy 2.0.48, Alembic 1.18.4 | [Issue #26403 / Discussion #26635](https://github.com/open-webui/open-webui/discussions/26635) reports JSON double encoding and broken Pydantic login parsing | Executed original migration + a standalone Pydantic type probe, not an HTTP login request or full historical version chain |
| Drizzle ORM | `drizzle-orm@0.44.7` real synchronous migrator and better-sqlite3, using a frozen SQL table-rebuild template transcribed from reported steps | [Issue #5782](https://github.com/drizzle-team/drizzle-orm/issues/5782) reports silent cascading data deletion and a completed migration journal | Executed the real ORM migration runner, independent SQL joins, foreign key checks, and SQLite integrity checks; not a complete affected Electron product |
| Django | 5.1.8, original [PetterS demo](https://github.com/PetterS/django-demo-app) SHA 8c62fd7c, plus actual contrib sites migrations | [Ticket #29843](https://code.djangoproject.com/ticket/29843) describes late permission creation and a migration failure | Direct path genuinely failed; staged path passed, so it is **excluded** from the same-ledger-success positive group |

The original source ZIP's N22 initial observation (fresh versus staged Django
sites without edits) was confirmed again on this Linux/Python runtime.

## RQ1. Can both paths report identical schema/ledger and still disagree?

**Yes, in two independently documented project mechanisms.**

### Open WebUI — typed payload semantics

For a pre-existing single user whose settings payload is a valid JSON object,
the historical migration completes and advances the Alembic revision ledger.
Its SQLAlchemy `JSON` column stores a JSON-encoded **string**, because the
migration already calls `json.dumps()` before SQLAlchemy serializes again.
This remains syntactically valid JSON and survives schema, version and
cardinality checks, yet a Pydantic model requiring a dictionary rejects it.

With **two or more** users, a separate SQLAlchemy column-rebinding bug raises
an exception mid-migration. We verified the failure boundary and did not
count these runs as converged outcomes.

An empty object becoming `NULL` is separately reported in raw results, but
we exclude this case from primary success/bug scoring because the required
business distinction between the two has not been independently established.

### Drizzle ORM — referential data semantics

With SQLite foreign keys enabled, the Drizzle migrator starts a transaction
before running generated-style `PRAGMA foreign_keys=OFF`. SQLite ignores
this pragma inside a transaction. Dropping the old parent table then fires
the originally declared `ON DELETE CASCADE`, deleting children and their
attachments, while the parent is reinserted and the migration journal
advances. The resulting database reports `PRAGMA integrity_check = ok` and
has no broken foreign keys, because the lost records are no longer present.

With `ON DELETE SET NULL`, **all table row counts are unchanged** but child
links are lost. We verified this additional mechanism-derived case on actual
SQLite; the referenced public report focuses primarily on CASCADE.
The protected path sets the pragma before Drizzle begins its transaction,
preserving these links in the same final schema/ledger.

With `NO ACTION` or `RESTRICT`, the original migration returns a foreign
key error and does not advance its ledger. These were executed, but are not
misrepresented as silent successes.

### Django — limits and negative controls

Running the upstream PetterS migration chain in one command raises a missing
permission exception. Staging individual migration targets succeeds. At an
earlier, structurally convergent checkpoint, staged and direct paths differ
by the extra *historical* `can_smell` permission, which is not a currently
required `can_hear` authorization. A raw diff should **not** equate that
difference to a present-day missing capability.

A customer-edited default Django Site domain also differs from a pristine
database without violating the current Site lookup contract. This is a real
user-intent negative control and would be a false alarm for naive row equality.

## RQ2. Detector comparison on the explicitly selected scenarios

The seven upstream/reference comparisons per Open WebUI and Drizzle plus
the Django probes generated **13 candidate convergent cases**. We excluded
one ambiguous JSON-empty/NULL case; **12 scenarios remain: 6 true-defect
conditions, 6 valid conditions.** These are *scenario counts*, not six
independent industrial incidents: positive conditions cluster into just
two source-project mechanisms.

| Check | Found out of 6 labelled defects | False alarms out of 6 valid cases |
| --- | ---: | ---: |
| Schema + migration ledger | 0 | 0 |
| Schema + ledger + per-table row counts | 3 | 1 |
| Raw data snapshot equality | 6 | 2 |
| Domain-aware, typed contract probes | 6 | 0 |

Untyped JSON syntax checks independently detected **0/2** Open WebUI
type-corruption scenarios, because the double-encoded strings remain valid
JSON. That check has no meaningful application to the other projects and
should **not** be read as a general baseline.

For the **contract probes in this curated sample only**, recall is
`6/6 = 100%` and false-positive proportion is `0/6 = 0%`. The
corresponding naive Wilson 95% descriptive intervals are
`[60.97%, 100%]` and `[0%, 39.03%]`. Because scenarios share
code paths, these are **not valid population confidence intervals**.
In particular, **FPR ≤5% has not been established.**

The 50 percentage point recall difference against row-count checks on these
six selected conditions is **not** evidence of a ≥15 percentage point
advantage against full project-specific migration/application tests.
A complete application test suite that states these same contracts can
reach identical correctness. The project was not evaluated against that
strong baseline at equal development and CI replay cost.

## RQ3. Local reproduction and cost

- The full independent download-and-execute script completed locally,
  including the pinned Open WebUI version, PetterS source replay, real Drizzle
  runner, and an evidence recomputation stage.
- Four automated consistency tests passed. Results include per-case SQL
  databases and the full observed rows, hashes, ledgers, subprocess exit
  codes and error tails.
- Local Open WebUI migration bodies took on the order of tens of milliseconds;
  the small Drizzle cases on the order of a few milliseconds. This is not
  deployment throughput or full release-upgrade time.
- Two selected standalone SQLite read queries were measured in the low
  microsecond range (tiny local datasets, 200 repetitions).
- In a **separate synthetic** 10,000-row-per-table scale test, the pair of
  semantic SQL gates took a median of approximately **1.37 ms**, versus
  approximately **0.01 ms** for schema/ledger enumeration (30 warmed repeats).
  This shows a data-scan cost, not a production estimate.
- No real developer minutes, CI queue time, business recovery costs, SaaS
  revenue, or customer frequency were measured. No industrial ROI claim is
  supported.

## Threats and publication readiness

1. **Case selection after discovery:** public reports guided both selected
   positive mechanisms and the checks. There is no truly held-out test,
   prospective hypothesis execution, or independent human adjudication.
2. **Small, constructed old-version databases:** actual public migration code
   is executed, but input records are fictional. The full Open WebUI release
   migration sequence, full-stack login tests, Drizzle Kit regeneration in the
   original consumer, and diverse backend/platform runs remain open.
3. **Strongest baseline absent:** domain-aware assertions are familiar
   engineering practice. We cannot claim a new general detector simply by
   writing the correct assertions and comparing to weaker structural checks.
4. **Evidence independence:** there are 6 positive controlled variants but
   only 2 independent source-project mechanisms. Pooled statistical analysis
   across scenarios is descriptive and should not be used to estimate
   industrial prevalence or recall.
5. **Legitimate evolution:** user-edited Site data and historical permissions
   demonstrate why arbitrary row differences are not faults. More negative
   controls across real projects are needed.
6. **Original preregistered N22 stopping criterion remains unmet:** the
   project-specific strong-baseline ≥15pp gain, independent holdout, and FPR
   ≤5% evidence are not established.

## Paper-safe conclusion

*We replicated two independent, publicly reported migration-failure
mechanisms in which successful SQLite migrations reached the same schema
and version ledger as a protected reference path while application-relevant
data were corrupted or disconnected. Structural checks alone did not expose
these particular failures. Explicit, domain-specific data and read-path
assertions detected the six curated fault conditions without alerting on six
curated negatives, but the result is exploratory, does not beat comprehensive
application testing, and cannot estimate industrial incidence or false-alarm
rates.*

This package is a defensible experimental foundation, **not a claim that all
experiments needed for an FSE Industry paper have been completed**.

Additional gate-by-gate requirements are in [SUBMISSION_GAPS.md](SUBMISSION_GAPS.md).
