/**
 * FAS 3 - Memory Driver Registry
 * Switches between drivers based on environment
 */

import type { Memory } from "./types";
import { InMemoryMemory } from "./inMemory";
import { createSqliteMemory } from "./sqlite";

let memory: Memory;

switch (process.env.MEMORY_DRIVER) {
  case "sqlite":
    memory = createSqliteMemory(process.env.SQLITE_PATH);
    break;
  default:
    memory = InMemoryMemory;
}

export default memory;