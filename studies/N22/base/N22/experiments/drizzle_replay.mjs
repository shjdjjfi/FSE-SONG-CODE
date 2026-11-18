/* Actual drizzle-orm@0.44.7 SQLite dialect + better-sqlite3 migration replay.
 * Public reference: https://github.com/drizzle-team/drizzle-orm/issues/5782
 * Migration SQL mirrors the reporter's Drizzle Kit table-rebuild template,
 * hand-transcribed and frozen here (NOT claimed as a generated tool output).
 * All data is seeded into isolated test databases; no external DB is touched.
 */

import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import { migrate } from 'drizzle-orm/better-sqlite3/migrator';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(here, '..');
const folder = path.resolve(projectDir, 'fixtures/drizzle_cascade');
const outIndex = process.argv.indexOf('--output');
const output = outIndex === -1
  ? path.resolve(projectDir, 'results/drizzle')
  : path.resolve(process.argv[outIndex + 1]);
fs.mkdirSync(output, { recursive: true });

const cases = [
  { name: 'cascade_three', policy: 'CASCADE', count: 3, userEdit: false },
  { name: 'cascade_one', policy: 'CASCADE', count: 1, userEdit: false },
  { name: 'cascade_zero', policy: 'CASCADE', count: 0, userEdit: false },
  { name: 'cascade_user_edit', policy: 'CASCADE', count: 3, userEdit: true },
  { name: 'set_null_three', policy: 'SET NULL', count: 3, userEdit: false },
  { name: 'no_action_three', policy: 'NO ACTION', count: 3, userEdit: false },
  { name: 'restrict_three', policy: 'RESTRICT', count: 3, userEdit: false },
];

function queryAll(db, query) {
  return db.prepare(query).all();
}

function createSeededDB(filename, spec) {
  if (fs.existsSync(filename)) fs.unlinkSync(filename);
  const db = new Database(filename);
  db.pragma('foreign_keys=ON');
  const constraint = spec.policy;
  // The policy is selected exclusively from the fixed, hardcoded matrix above.
  db.exec(
    'CREATE TABLE parent (id TEXT PRIMARY KEY NOT NULL, mode TEXT NOT NULL DEFAULT \'preview\');'
    + 'CREATE TABLE child (id TEXT PRIMARY KEY NOT NULL, parent_id TEXT '
    + 'REFERENCES parent(id) ON DELETE ' + constraint + ', payload TEXT NOT NULL);'
    + 'CREATE TABLE grandchild (id TEXT PRIMARY KEY NOT NULL, child_id TEXT '
    + 'NOT NULL REFERENCES child(id) ON DELETE CASCADE, payload TEXT NOT NULL);'
    + 'INSERT INTO parent(id,mode) VALUES (\'parent-1\',\'preview\');'
  );
  for (let i = 0; i < spec.count; i += 1) {
    const payload = spec.userEdit && i === 0 ? 'customer-changed' : 'note-' + i;
    db.prepare('INSERT INTO child(id,parent_id,payload) VALUES (?,?,?)')
      .run('c' + i, 'parent-1', payload);
    db.prepare('INSERT INTO grandchild(id,child_id,payload) VALUES (?,?,?)')
      .run('g' + i, 'c' + i, 'attachment-' + i);
  }
  return db;
}

function snapshot(db) {
  return {
    schema: queryAll(db,
      "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' AND type IN ('table','index','view','trigger') ORDER BY name"),
    journal: db.prepare('SELECT hash,created_at FROM __drizzle_migrations ORDER BY created_at').all(),
    parent: queryAll(db, 'SELECT * FROM parent ORDER BY id'),
    child: queryAll(db, 'SELECT * FROM child ORDER BY id'),
    grandchild: queryAll(db, 'SELECT * FROM grandchild ORDER BY id'),
    foreign_key_check: db.pragma('foreign_key_check'),
    integrity_check: db.pragma('integrity_check'),
    fk_setting: db.pragma('foreign_keys', { simple: true }),
  };
}

function runOne(spec, arm) {
  const filename = path.join(output, spec.name + '__' + arm + '.sqlite');
  const db = createSeededDB(filename, spec);
  const pre = {
    parent: queryAll(db, 'SELECT * FROM parent ORDER BY id'),
    child: queryAll(db, 'SELECT * FROM child ORDER BY id'),
    grandchild: queryAll(db, 'SELECT * FROM grandchild ORDER BY id'),
  };
  let success = false;
  let error = null;
  const start = process.hrtime.bigint();
  // Reference protection is the publicly documented workaround, not a
  // claim that the upstream library implements it.
  if (arm === 'reference_fk_before_begin') db.pragma('foreign_keys=OFF');
  try {
    migrate(drizzle(db), { migrationsFolder: folder });
    success = true;
  } catch (ex) {
    error = ex.name + ': ' + ex.message;
  } finally {
    db.pragma('foreign_keys=ON');
  }
  const migrationMs = Number(process.hrtime.bigint() - start) / 1e6;
  const after = snapshot(db);
  const lostChildren = pre.child.filter(
    old => !after.child.some(now => now.id === old.id && now.parent_id === old.parent_id && now.payload === old.payload)
  );
  const lostAttachments = pre.grandchild.filter(
    old => !after.grandchild.some(now => now.id === old.id && now.child_id === old.child_id && now.payload === old.payload)
  );
  const record = {
    id: spec.name + '__' + arm,
    project: 'drizzle-orm',
    source_class: 'real_drizzle_runtime_with_issue_derived_sqlite_rebuild',
    scenario: spec.name,
    arm, policy: spec.policy, input_children: spec.count, legitimate_user_edit: spec.userEdit,
    success, error, migration_ms: Number(migrationMs.toFixed(3)),
    sqlite_file: path.basename(filename),
    pre, ...after,
    data_contract_preserved: lostChildren.length === 0 && lostAttachments.length === 0,
    absent_or_mutated_children: lostChildren,
    absent_or_mutated_attachments: lostAttachments,
    application_lookup_success: pre.child.every(old =>
      after.child.some(now => now.id === old.id && now.parent_id === old.parent_id && now.payload === old.payload)
    ),
  };
  db.close();
  return record;
}

const rows = [];
for (const spec of cases) {
  for (const arm of ['upstream', 'reference_fk_before_begin']) {
    rows.push(runOne(spec, arm));
  }
}
for (const spec of cases) {
  const bad = rows.find(r => r.id === spec.name + '__upstream');
  const good = rows.find(r => r.id === spec.name + '__reference_fk_before_begin');
  for (const row of [bad, good]) {
    row.same_schema_as_reference = JSON.stringify(row.schema) === JSON.stringify(good.schema);
    row.same_ledger_as_reference = JSON.stringify(row.journal) === JSON.stringify(good.journal);
    row.same_row_counts_as_reference = row.child.length === good.child.length
      && row.grandchild.length === good.grandchild.length;
  }
}
const sqlPath = path.join(folder, '0000_rebuild_parent.sql');
const outputResult = {
  input: {
    issue: 'https://github.com/drizzle-team/drizzle-orm/issues/5782',
    runtime_version: 'drizzle-orm@0.44.7',
    driver: 'better-sqlite3@12.6.2',
    node: process.version,
    platform: os.platform(),
    sqlite: rows[0].integrity_check,
    sql_sha256: createHash('sha256').update(fs.readFileSync(sqlPath)).digest('hex'),
    sql_template_transcribed_not_generated: true,
  },
  runs: rows,
};
fs.writeFileSync(
  path.join(output, 'drizzle-observations.json'),
  JSON.stringify(outputResult, null, 2),
);
for (const row of rows) {
  console.log(row.id, 'exit=', row.success,
    'schema=', row.same_schema_as_reference,
    'ledger=', row.same_ledger_as_reference,
    'rowcount=', row.same_row_counts_as_reference,
    'contract=', row.data_contract_preserved,
  );
}
