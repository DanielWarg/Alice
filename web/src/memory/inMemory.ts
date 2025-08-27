/**
 * FAS 3 - In-Memory Driver (No dependencies fallback)
 */

import type { Artifact, Memory, ArtifactKind } from "./types";
import { randomUUID } from "crypto";

const store = new Map<string, Artifact[]>(); // key=userId

export const InMemoryMemory: Memory = {
  async write(a: Artifact) {
    const id = a.id || randomUUID();
    const arr = store.get(a.userId) || [];
    
    // Add to beginning and cap at 500 items
    arr.unshift({ ...a, id });
    store.set(a.userId, arr.slice(0, 500));
  },

  async fetch(userId: string, k: number, kinds?: ArtifactKind[]) {
    let arr = store.get(userId) || [];
    
    // Filter by kinds if specified
    if (kinds?.length) {
      arr = arr.filter(a => kinds.includes(a.kind));
    }
    
    // Filter out expired artifacts
    const now = new Date();
    arr = arr.filter(a => !a.expiresAt || new Date(a.expiresAt) > now);
    
    // Sort by score (descending) and return top k
    return arr
      .sort((a, b) => (b.score - a.score))
      .slice(0, k);
  }
};