/**
 * Drive this TypeScript verifier through the corpus's adapter contract.
 *
 *   npm run build
 *   cd ../../vectors
 *   python3 run.py --impl "node ../verifiers/typescript/dist/adapter.js"
 *
 * `run-vectors.ts` scans the whole corpus and checks it internally, which
 * is what `npm test` runs. This file does the other thing: one vector per
 * invocation, one line of stdout, so an independent implementation and this
 * one go through exactly the same harness and produce diffable output.
 *
 * The contract, in full - read the vector named on argv[2], replay it, and
 * print either:
 *
 *   ACCEPT <state_hash> <record_count> <account>=<balance> ...
 *   REJECT
 */

import { createPrivateKey, createPublicKey } from "node:crypto";
import { readFileSync } from "node:fs";

import {
  replay,
  stateHash,
  demoVerifier,
  hmacVerifier,
  ed25519Verifier,
  SatRootError,
  type Event,
  type Verifier,
} from "./satroot.js";

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
  scheme: string;
  events: Event[];
}

function main(): void {
  const path = process.argv[2];
  if (path === undefined) {
    console.error("usage: node adapter.js <vector.json>");
    process.exit(2);
  }

  const vector = JSON.parse(readFileSync(path, "utf8")) as Vector;
  const verifier = verifierFor(vector.scheme);

  let state;
  try {
    state = replay(vector.events, verifier);
  } catch (err) {
    // Only a protocol rejection means REJECT. Anything else is a fault in
    // this adapter, and reporting it as a rejection would turn a crash into
    // a passing rejection vector - agreement manufactured out of a bug.
    if (err instanceof SatRootError) {
      console.log("REJECT");
      return;
    }
    throw err;
  }

  const terms: string[] = [];
  for (const [account, balance] of [...state.balances.entries()].sort()) {
    if (balance !== 0n) terms.push(`${account}=${balance.toString()}`);
  }

  console.log(
    ["ACCEPT", stateHash(state), String(vector.events.length), ...terms].join(" "),
  );
}

main();
