/**
 * FAS 3 - SQLite Memory Driver
 * Production-ready persistence with vector search capability
 */

import Database from "better-sqlite3";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";
import type { Memory, Artifact, ArtifactKind } from "./types";

type SqliteRow = {
  id: string; user_id: string; kind: string; text: string; score: number;
  expires_at: string | null; meta_json: string | null; embedding: Buffer | null; created_at: string;
};

function toBuf(vec?: number[]): Buffer | null {
  if (!vec || !vec.length) return null;
  const f32 = new Float32Array(vec);
  return Buffer.from(f32.buffer);
}

function fromBuf(buf: Buffer | null): number[] | undefined {
  if (!buf) return undefined;
  const f32 = new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.byteLength / 4));
  return Array.from(f32);
}

function cosine(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length && i < b.length; i++) {
    dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb) || 1e-9;
  return dot / denom;
}

function ensureDir(p: string) {
  const d = path.dirname(p); 
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}

function ensureSchema(db: Database.Database) {
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      kind TEXT NOT NULL,
      text TEXT NOT NULL,
      score REAL NOT NULL DEFAULT 0.0,
      expires_at TEXT,
      meta_json TEXT,
      embedding BLOB,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_artifacts_user_kind_score ON artifacts(user_id, kind, score DESC, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_artifacts_expiry ON artifacts(expires_at);
  `);
}

export function createSqliteMemory(dbPath = process.env.SQLITE_PATH || "./data/alice.db"): Memory & {
  searchSimilar?: (userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) => Promise<Artifact[]>;
} {
  ensureDir(dbPath);
  const db = new Database(dbPath);
  ensureSchema(db);

  // Prepared statements
  const upsert = db.prepare(`
    INSERT INTO artifacts (id, user_id, kind, text, score, expires_at, meta_json, embedding)
    VALUES (@id, @user_id, @kind, @text, @score, @expires_at, @meta_json, @embedding)
    ON CONFLICT(id) DO UPDATE SET
      user_id=excluded.user_id, kind=excluded.kind, text=excluded.text,
      score=excluded.score, expires_at=excluded.expires_at,
      meta_json=excluded.meta_json, embedding=excluded.embedding
  `);

  // We'll prepare statements dynamically based on the kinds filter
  const selectAllSql = `
    SELECT * FROM artifacts
     WHERE user_id = ? 
       AND (expires_at IS NULL OR expires_at > datetime('now'))
     ORDER BY score DESC, created_at DESC
     LIMIT ?
  `;

  const selectAll = db.prepare(selectAllSql);

  const api: Memory & {
    searchSimilar?: (userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) => Promise<Artifact[]>;
  } = {
    async write(a: Artifact) {
      const id = a.id || randomUUID();
      upsert.run({
        id,
        user_id: a.userId,
        kind: a.kind,
        text: a.text,
        score: a.score ?? 0,
        expires_at: a.expiresAt ?? null,
        meta_json: a.meta ? JSON.stringify(a.meta) : null,
        embedding: toBuf(a.embedding)
      });
    },

    async fetch(userId: string, k: number, kinds?: ArtifactKind[]) {
      // Get all artifacts for user
      const rows = selectAll.all(userId, k) as SqliteRow[];
      
      // Filter by kinds if specified (post-query filtering for simplicity)
      let filteredRows = rows;
      if (kinds && kinds.length > 0) {
        filteredRows = rows.filter(r => kinds.includes(r.kind as ArtifactKind));
      }
      
      // Take top k after filtering
      const topRows = filteredRows.slice(0, k);
      
      return topRows.map(r => ({
        id: r.id,
        userId: r.user_id,
        kind: r.kind as ArtifactKind,
        text: r.text,
        score: r.score,
        expiresAt: r.expires_at || undefined,
        meta: r.meta_json ? JSON.parse(r.meta_json) : undefined,
        embedding: fromBuf(r.embedding)
      }));
    },

    // Vector similarity search (JS fallback)
    async searchSimilar(userId: string, queryEmb: number[], k: number, kinds?: ArtifactKind[]) {
      const candidates = await this.fetch(userId, 500, kinds); // Get more candidates
      const scored = candidates
        .filter(c => Array.isArray(c.embedding) && c.embedding.length)
        .map(c => ({ c, sim: cosine(queryEmb, c.embedding as number[]) }))
        .sort((a, b) => b.sim - a.sim)
        .slice(0, k)
        .map(x => x.c);
      
      return scored.length ? scored : candidates.slice(0, k);
    }
  };

  return api;
}