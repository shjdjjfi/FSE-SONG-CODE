// N22 research harness: executes the unmodified upstream v2.0.19 migration.
// This file is an external experiment, NOT part of the upstream release.
import { test, expect } from "bun:test"
import { SqliteClient } from "@effect/sql-sqlite-bun"
import { EffectDrizzleSqlite } from "@opencode/core/database/drizzle"
import { Database } from "@opencode/core/database/database"
import { DatabaseMigration } from "@opencode/core/database/migration"
import { V1Migration } from "@opencode/core/database/v1-migration"
import { Global } from "@opencode/util/global"
import { Effect, Scope } from "effect"
import { sql } from "drizzle-orm"
import type { SqlClient } from "effect/unstable/sql/SqlClient"
import path from "node:path"
import { createHash } from "node:crypto"

const makeDb = EffectDrizzleSqlite.makeWithDefaults()
const sha = (data: unknown) => createHash("sha256").update(JSON.stringify(data)).digest("hex")
const run = <A, E>(effect: Effect.Effect<A, E, SqlClient | Scope.Scope | Global.Service>) =>
  Effect.runPromise(
    Effect.scoped(
      effect.pipe(
        Effect.provideService(Global.Service, Global.make({ data: path.join(process.cwd(), ".n22-data") })),
        Effect.provide(SqliteClient.layer({ filename: ":memory:", disableWAL: true })),
      ),
    ),
  )

const assistantPayload = (withAgent: boolean) => ({
  role: "assistant",
  time: { created: 20, completed: 25 },
  parentID: "msg_000000000001aaaaaaaaaaaaaa",
  modelID: "model",
  providerID: "provider",
  mode: "build",
  ...(withAgent ? { agent: "build" } : {}),
  path: { cwd: "/tmp/n22", root: "/tmp/n22" },
  cost: 1,
  tokens: { total: 10, input: 2, output: 3, reasoning: 4, cache: { read: 5, write: 6 } },
})

type Scenario = "early_agent_missing" | "agent_present" | "mode_backfill" | "late_session" | "no_late_session"

const scenarios: readonly Scenario[] = [
  "early_agent_missing", "agent_present", "mode_backfill", "late_session", "no_late_session",
]

function runner(caseID: Scenario) {
  return run(
    Effect.gen(function* () {
      const db = yield* makeDb
      yield* DatabaseMigration.apply(db)
      for (const ddl of [
        `CREATE TABLE session (id text PRIMARY KEY, project_id text NOT NULL, workspace_id text,
          parent_id text, slug text NOT NULL, directory text NOT NULL, path text, title text NOT NULL,
          version text NOT NULL, share_url text, summary_additions integer, summary_deletions integer,
          summary_files integer, summary_diffs text, metadata text, cost real DEFAULT 0 NOT NULL,
          tokens_input integer DEFAULT 0 NOT NULL, tokens_output integer DEFAULT 0 NOT NULL,
          tokens_reasoning integer DEFAULT 0 NOT NULL, tokens_cache_read integer DEFAULT 0 NOT NULL,
          tokens_cache_write integer DEFAULT 0 NOT NULL, revert text, permission text, agent text,
          model text, time_created integer NOT NULL, time_updated integer NOT NULL,
          time_compacting integer, time_archived integer)`,
        `CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL, time_created integer NOT NULL,
          time_updated integer NOT NULL, data text NOT NULL)`,
        `CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
          time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL)`,
      ]) yield* db.run(sql.raw(ddl))

      return yield* Effect.gen(function* () {
        const first = "ses_test"
        const msg = "msg_000000000001aaaaaaaaaaaaaa"
        const asst = "msg_000000000002aaaaaaaaaaaaaa"
        yield* db.run(sql`INSERT INTO project (id, worktree, time_created, time_updated, sandboxes)
          VALUES ('global', '/tmp/n22', 1, 2, '[]')`)
        yield* db.run(sql`INSERT INTO session (id, project_id, slug, directory, title, version, time_created, time_updated)
          VALUES (${first}, 'global', 'test', '/tmp/n22', 'Test', '1', 1, 2)`)

        if (caseID === "late_session" || caseID === "no_late_session") {
          yield* db.run(sql`INSERT INTO message (id, session_id, time_created, time_updated, data)
            VALUES (${msg}, ${first}, 10, 11, ${JSON.stringify({ role: "user", time: { created: 10 }, agent: "build",
              model: { providerID: "provider", modelID: "model" } })})`)
          yield* V1Migration.run()
          if (caseID === "late_session") {
            // A still-running V1 client creates a second session after V2 checkpointed.
            yield* db.run(sql`INSERT INTO session (id, project_id, slug, directory, title, version, time_created, time_updated)
              VALUES ('ses_late', 'global', 'late', '/tmp/n22', 'Late', '1', 30, 31)`)
            yield* db.run(sql`INSERT INTO message (id, session_id, time_created, time_updated, data)
              VALUES ('msg_000000000003aaaaaaaaaaaaaa', 'ses_late', 32, 33, ${JSON.stringify({
                role: "user", time: { created: 32 }, agent: "build", model: { providerID: "provider", modelID: "model" },
              })})`)
          }
        } else {
          yield* db.run(sql`INSERT INTO message (id, session_id, time_created, time_updated, data)
            VALUES (${msg}, ${first}, 10, 11, ${JSON.stringify({ role: "user", time: { created: 10 }, agent: "build",
              model: { providerID: "provider", modelID: "model" } })})`)
          const withAgent = caseID !== "early_agent_missing"
          // mode_backfill is a counterfactual, explicitly labeled as preprocessing.
          yield* db.run(sql`INSERT INTO message (id, session_id, time_created, time_updated, data)
            VALUES (${asst}, ${first}, 20, 21, ${JSON.stringify(assistantPayload(withAgent))})`)
        }

        const start = performance.now()
        const runResult = yield* V1Migration.run()
        const elapsed = performance.now() - start
        const migrationState = yield* db.get<{ value: string }>(sql`SELECT value FROM kv WHERE key='migration.v1-v2'`)
        const sourceIDs = yield* db.all<{ id: string }>(sql`SELECT id FROM message ORDER BY id`)
        const targetIDs = yield* db.all<{ id: string }>(sql`SELECT id FROM session_message ORDER BY id`)
        const sourceSessions = yield* db.all<{ id: string }>(sql`SELECT id FROM session ORDER BY id`)
        const targetSessions = yield* db.all<{ id: string }>(sql`SELECT id FROM session_v2 ORDER BY id`)
        const schema = yield* db.all(sql`SELECT type, name, tbl_name, sql FROM sqlite_master
          WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type,name`)
        const migrationTables = yield* db.all(sql`SELECT name FROM sqlite_master
          WHERE type='table' AND name LIKE '%migration%' ORDER BY name`)
        const ledger = yield* db.all(sql`SELECT id FROM migration ORDER BY id`)
        return {
          case_id: caseID,
          migration_status: runResult.status,
          checkpoint: migrationState?.value,
          source_messages: sourceIDs.map((r) => r.id),
          projected_messages: targetIDs.map((r) => r.id),
          source_sessions: sourceSessions.map((r) => r.id),
          projected_sessions: targetSessions.map((r) => r.id),
          schema_sha256: sha(schema),
          ledger_sha256: sha(ledger),
          migration_tables: migrationTables,
          observed_missing_source_messages: sourceIDs.map((r) => r.id).filter((id) => !targetIDs.some((r) => r.id === id)),
          observed_missing_source_sessions: sourceSessions.map((r) => r.id).filter((id) => !targetSessions.some((r) => r.id === id)),
          elapsed_milliseconds: Number(elapsed.toFixed(3)),
        }
      }).pipe(Effect.provideService(Database.Service, { db }))
    }),
  )
}

test("N22: unchanged upstream migration misses historically valid rows and late V1 sessions", async () => {
  for (const scenario of scenarios) {
    const result = await runner(scenario)
    expect(result.migration_status).toBe("completed")
    expect(result.checkpoint).toBe('{"phase":"completed"}')
    if (scenario === "early_agent_missing") {
      expect(result.source_messages.length).toBe(2)
      expect(result.projected_messages.length).toBe(1)
      expect(result.observed_missing_source_messages.length).toBe(1)
    } else if (scenario === "late_session") {
      expect(result.source_sessions.length).toBe(2)
      expect(result.projected_sessions.length).toBe(1)
      expect(result.observed_missing_source_sessions).toEqual(["ses_late"])
    } else {
      expect(result.observed_missing_source_messages).toEqual([])
      expect(result.observed_missing_source_sessions).toEqual([])
    }
    console.log("N22_CASE_JSON " + JSON.stringify(result))
  }
})
