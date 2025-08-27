/**
 * FAS 3 - Memory & RAG Types
 * Artifact-based memory system
 */

export type ArtifactKind = "insight" | "kb_chunk" | "plan" | "policy" | "vision_event";

export interface Artifact {
  id: string;
  userId: string;
  kind: ArtifactKind;
  text: string;
  score: number;                 // 0..1
  expiresAt?: string;            // ISO timestamp
  meta?: Record<string, any>;
  embedding?: number[];          // for vector search
}

export interface Memory {
  write(a: Artifact): Promise<void>;
  fetch(userId: string, k: number, kinds?: ArtifactKind[]): Promise<Artifact[]>;
}