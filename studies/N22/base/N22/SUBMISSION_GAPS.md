# N22 evidence gates before declaring an FSE Industry submission complete

## What is done

- [x] Two independent public migration-defect mechanisms located, with
  publicly documented symptoms and source provenance.
- [x] Real Open WebUI Alembic migration body executed against SQLite, with
  an isolated reference patch and both silent and hard-failure boundary cases.
- [x] Real Drizzle ORM 0.44.7 SQLite migrator executed with an issue-derived,
  explicit table-rebuild fixture; compared against public FK pre-transaction
  protection; checked schema, version journal and application data links.
- [x] Real Django 5.1.8 reproduction of the upstream permission ordering issue.
- [x] Real Django/SQLite fresh, staged, and user-edited negative controls.
- [x] Pre/Post SQLite snapshots, typed data contracts, schema/ledger and row
  count baselines, full raw result JSON, tests, and local CI workflow.
- [x] Exploratory, non-industrial performance probes with typed SQL checks.

## What is **not** done

1. **Full historical upgrade chains:** Open WebUI's actual v0.4.7→v0.9.6
   release chain and full app login have not been run. Our old-version input
   is a representative, seeded SQLite table, and the typed app behavior probe
   is standalone Pydantic. Drizzle's SQL is a faithful issue-derived fixture,
   not a fresh Drizzle Kit 0.31.7 generation on the affected consumer project.
2. **Independent, blinded holdout:** case selection and contract construction
   followed public bug reports. A separate issue-blind project holdout with
   maintenance-verified labels has not been gathered.
3. **Strongest practice baselines:** comparison against integrated
   application migration tests (for example django-test-migrations plus
   application assertions) under equal authoring and CI replay cost is
   incomplete. In principle such tests can match all reported contract checks;
   no ≥15 percentage point superiority is demonstrated.
4. **Industrial frequency/impact:** we have no continuous release or migration
   denominator, deployed customer DB snapshots, incident response logs,
   end-user loss estimates, or production rollback cost. These cannot be
   reconstructed legitimately from selected public bug reports.
5. **Generalizability:** only SQLite in one Linux environment is measured;
   PostgreSQL/MariaDB, Windows/macOS, database size distributions,
   migration forks, and different ORM versions remain unmeasured.
6. **Statistical assurance:** with only six negative scenarios, observing
   zero contract false alarms gives a naive Wilson 95% upper bound of ~39%.
   The points share project mechanisms, so even that interval is not an
   independent-sample industrial interval. FPR ≤5% is **not** established.
7. **Original N22 stop rule:** obtaining ≥2 cases is now substantively
   supported by two public mechanisms, but its *independent holdout* and
   *≥15pp advantage over complete baselines at equal replay budget* requirements
   remain unsatisfied. The original prespecified rule must not be marked met.
8. **Novelty and practitioner study:** structured business-data assertions
   and migration replay are existing engineering practices. A distinguishable
   method contribution or a significantly broader independent industrial
   measurement study, plus a validated engineering cost model, is needed.

## Honest suggested submission direction

Treat N22 as an empirical measurement/replication study of failures that
structural migration checks cannot certify. Do not claim a newly invented
general-purpose fault detector. The strongest next extension is a curator-blind
collection of public migration histories with maintainer-confirmed contracts
and reproduction-ready old-version DBs, comparing contract probes against the
projects' own complete test suites.

FSE 2027 Industry CFP: https://conf.researchr.org/track/fse-2027/fse-2027-industry-papers

- Short paper: 5 content pages + 1 references page
- Long paper: 10 content pages + 2 references pages
- Due: 23 January 2027, AoE
- Industry motivated public research can be eligible, but convincing industrial
  applicability, soundness, breadth and lessons must be shown.
