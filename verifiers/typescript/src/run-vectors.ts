/**
 * Run the SATROOT-1 conformance corpus against this TypeScript verifier.
 *
 *   npm test          # from verifiers/typescript
 *
 * Exits non-zero if any vector disagrees with its recorded expectation.
 */

import { createPrivateKey, createPublicKey } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import {
  replay,
  parseLedgerJson,
  compareCodePoints,
  stateHash,
  demoVerifier,
  hmacVerifier,
  ed25519Verifier,
  SatRootError,
  type Event,
  type Verifier,
} from "./satroot.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const VECTORS_DIR = join(HERE, "..", "..", "..", "vectors");

// Fixed material documented in vectors/README.md.
const ED25519_PRIVATE_TO_PUBLIC: Record<string, string> = {
  "issuer-key": "11".repeat(32),
  "alice-key": "22".repeat(32),
};
const HMAC_SECRETS: Record<string, string> = {
  "issuer-key": "33".repeat(32),
  "alice-key": "44".repeat(32),
};

/** Derive the Ed25519 public keys from the corpus's fixed private keys. */
function ed25519PublicKeys(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [keyId, privHex] of Object.entries(ED25519_PRIVATE_TO_PUBLIC)) {
    const pkcs8 = Buffer.concat([
      Buffer.from("302e020100300506032b657004220420", "hex"),
      Buffer.from(privHex, "hex"),
    ]);
    const priv = createPrivateKey({ key: pkcs8, format: "der", type: "pkcs8" });
    const spki = createPublicKey(priv).export({ format: "der", type: "spki" }) as Buffer;
    out[keyId] = spki.subarray(spki.length - 32).toString("hex");
  }
  return out;
}

function verifierFor(scheme: string): Verifier {
  if (scheme === "demo") return demoVerifier;
  if (scheme === "hmac-sha256") return hmacVerifier(HMAC_SECRETS);
  if (scheme === "ed25519") return ed25519Verifier(ed25519PublicKeys());
  throw new Error(`unknown scheme in vector: ${scheme}`);
}

interface Vector {
  name: string;
  scheme: string;
  events: Event[];
  options?: { allow_unbound_keys?: boolean; expected_genesis_event_id?: string };
  expect: {
    ok: boolean;
    final_state_hash?: string;
    balances?: Record<string, string>;
    record_count?: number;
  };
}

function checkVector(vector: Vector, text: string): string[] {
  const problems: string[] = [];
  let state;
  try {
    // Replay parses the text under the input profile (SPEC.md section 2.6a),
    // whatever was used to read the expectation.
    const strict = parseLedgerJson(text) as unknown as Vector;
    state = replay(strict.events, verifierFor(strict.scheme), {
      allowUnboundKeys: strict.options?.allow_unbound_keys === true,
      expectedGenesisEventId: strict.options?.expected_genesis_event_id,
    });
  } catch (err) {
    if (vector.expect.ok) {
      const msg = err instanceof SatRootError ? err.message : String(err);
      problems.push(`expected success, replay failed: ${msg}`);
    }
    return problems;
  }
  if (!vector.expect.ok) {
    problems.push("expected rejection, but replay succeeded");
    return problems;
  }
  const hash = stateHash(state);
  if (hash !== vector.expect.final_state_hash) {
    problems.push(`state hash mismatch: ${hash} != ${vector.expect.final_state_hash}`);
  }
  const balances = Object.create(null) as Record<string, string>;
  for (const [k, v] of [...state.balances.entries()].sort((x, y) => compareCodePoints(x[0], y[0]))) {
    if (v !== 0n) balances[k] = v.toString();
  }
  const expected = vector.expect.balances ?? {};
  if (JSON.stringify(balances) !== JSON.stringify(expected)) {
    problems.push(`balances mismatch: ${JSON.stringify(balances)} != ${JSON.stringify(expected)}`);
  }
  if (vector.events.length !== vector.expect.record_count) {
    problems.push("record count mismatch");
  }
  return problems;
}

function main(): number {
  const files = readdirSync(VECTORS_DIR).filter((f) => f.endsWith(".json")).sort();
  if (files.length === 0) {
    console.error(`no vectors found under ${VECTORS_DIR}`);
    return 1;
  }
  let failures = 0;
  for (const file of files) {
    const text = readFileSync(join(VECTORS_DIR, file), "utf8");
    // The expectation is read leniently: a vector may hold NaN or a duplicate
    // member on purpose, which JSON.parse refuses or flattens. When it cannot
    // be read at all, the file name says what is expected.
    let vector: Vector;
    try {
      vector = JSON.parse(text) as Vector;
    } catch {
      vector = { name: file.replace(/\.json$/, ""), scheme: "demo", events: [],
                 expect: { ok: !file.startsWith("reject-") } };
    }
    const problems = checkVector(vector, text);
    console.log(`${problems.length === 0 ? "ok  " : "FAIL"} ${vector.name}`);
    for (const p of problems) {
      console.log(`       - ${p}`);
      failures += 1;
    }
  }
  console.log(`${files.length} vectors, ${failures} failures`);
  return failures === 0 ? 0 : 1;
}

process.exit(main());
