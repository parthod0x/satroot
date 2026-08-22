/**
 * SATROOT-1 verifier — independent TypeScript implementation.
 *
 * Written from SPEC.md and the conformance corpus, not by porting the
 * Python reference. Its purpose is to demonstrate that the protocol is
 * implementable from its specification: it must reproduce byte-identical
 * canonical JSON, event ids, and state hashes, and make the same
 * accept/reject decision on every vector.
 *
 * No third-party dependencies; Node's built-in crypto only.
 */

import { createHash, createHmac, createPublicKey, verify as cryptoVerify } from "node:crypto";

export class SatRootError extends Error {}

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
export type Event = { [k: string]: Json };

/* ------------------------------------------------------------------ */
/* Canonicalization                                                    */
/* ------------------------------------------------------------------ */

/**
 * Canonical JSON: keys sorted, no whitespace, non-ASCII emitted raw.
 * Equivalent to Python's
 *   json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
 *
 * JSON.stringify already escapes strings the same way Python does with
 * ensure_ascii=False (short escapes for \b \t \n \f \r \" \\, \uXXXX for
 * other control characters), so string encoding is delegated to it.
 */
export function canonicalJson(value: Json): string {
  if (value === null || typeof value === "boolean" || typeof value === "number") {
    return JSON.stringify(value) as string;
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  const keys = Object.keys(value).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
}

export function sha256Hex(data: string): string {
  return createHash("sha256").update(Buffer.from(data, "utf8")).digest("hex");
}

function omit(event: Event, drop: string[]): Event {
  const out: Event = {};
  for (const k of Object.keys(event)) if (!drop.includes(k)) out[k] = event[k];
  return out;
}

/** Event id excludes `event_id` and `state_hash`. */
export function eventId(event: Event): string {
  return "sha256:" + sha256Hex(canonicalJson(omit(event, ["event_id", "state_hash"])));
}

/** Signing payload additionally excludes `signature`. */
export function signingPayload(event: Event): string {
  return canonicalJson(omit(event, ["signature", "event_id", "state_hash"]));
}

/* ------------------------------------------------------------------ */
/* Signature schemes                                                   */
/* ------------------------------------------------------------------ */

export type Verifier = (event: Event, payload: string) => boolean;

export const demoVerifier: Verifier = (event) =>
  (event["signature_scheme"] ?? "demo") === "demo" && event["signature"] === "demo";

export function hmacVerifier(secrets: Record<string, string>): Verifier {
  return (event, payload) => {
    if (event["signature_scheme"] !== "hmac-sha256") return false;
    const keyId = event["signature_key_id"];
    if (typeof keyId !== "string" || !keyId) return false;
    const secret = secrets[keyId];
    if (secret === undefined) return false;
    // The secret is used as its literal UTF-8 bytes, not decoded from hex.
    const digest = createHmac("sha256", Buffer.from(secret, "utf8"))
      .update(Buffer.from(payload, "utf8"))
      .digest("hex");
    return event["signature"] === "hmac-sha256:" + digest;
  };
}

/** Wrap a raw 32-byte Ed25519 public key in the SPKI envelope Node expects. */
function ed25519KeyFromRawHex(hex: string) {
  const spki = Buffer.concat([
    Buffer.from("302a300506032b6570032100", "hex"),
    Buffer.from(hex, "hex"),
  ]);
  return createPublicKey({ key: spki, format: "der", type: "spki" });
}

export function ed25519Verifier(publicKeys: Record<string, string>): Verifier {
  return (event, payload) => {
    if (event["signature_scheme"] !== "ed25519") return false;
    const keyId = event["signature_key_id"];
    if (typeof keyId !== "string" || !keyId) return false;
    const pubHex = publicKeys[keyId];
    const signature = event["signature"];
    if (pubHex === undefined || typeof signature !== "string") return false;
    if (!signature.startsWith("ed25519:")) return false;
    try {
      const sig = Buffer.from(signature.slice("ed25519:".length), "hex");
      if (sig.length !== 64) return false;
      return cryptoVerify(null, Buffer.from(payload, "utf8"), ed25519KeyFromRawHex(pubHex), sig);
    } catch {
      return false;
    }
  };
}

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */

export interface State {
  rootId: string;
  symbol: string;
  name: string;
  decimals: number;
  maxSupply: bigint | null;
  mintAuthority: string;
  profile: Json;
  profileMode: Json;
  balances: Map<string, bigint>;
  frozen: Set<string>;
  supply: bigint;
  sequence: number;
  lastEventId: string;
}

/** The commitment snapshot the state hash is taken over. */
export function commitmentSnapshot(s: State): Json {
  const balances: { [k: string]: Json } = {};
  for (const acct of [...s.balances.keys()].sort()) {
    const v = s.balances.get(acct)!;
    if (v !== 0n) balances[acct] = v.toString();
  }
  return {
    root_id: s.rootId,
    symbol: s.symbol,
    name: s.name,
    decimals: s.decimals,
    max_supply: s.maxSupply === null ? null : s.maxSupply.toString(),
    mint_authority: s.mintAuthority,
    profile: s.profile ?? null,
    profile_mode: s.profileMode ?? null,
    balances,
    frozen_accounts: [...s.frozen].sort(),
    supply: s.supply.toString(),
    sequence: s.sequence,
    last_event_id: s.lastEventId,
  };
}

export function stateHash(s: State): string {
  return "sha256:" + sha256Hex(canonicalJson(commitmentSnapshot(s)));
}

/* ------------------------------------------------------------------ */
/* Field parsing                                                       */
/* ------------------------------------------------------------------ */

const AMOUNT_RE = /^[0-9]+$/;

function parseAmount(value: Json): bigint {
  if (typeof value !== "string" || !AMOUNT_RE.test(value)) {
    throw new SatRootError(`invalid amount: ${JSON.stringify(value)}`);
  }
  return BigInt(value);
}

function parsePositiveAmount(value: Json): bigint {
  const amount = parseAmount(value);
  if (amount <= 0n) throw new SatRootError("amount must be positive");
  return amount;
}

function accountName(value: Json, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new SatRootError(`invalid account name for ${field}`);
  }
  return value;
}

function parseDecimals(value: Json): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0 || value > 18) {
    throw new SatRootError(`invalid decimals: ${JSON.stringify(value)}`);
  }
  return value;
}

function requireFields(event: Event, fields: string[]): void {
  for (const f of fields) {
    if (!(f in event) || event[f] === undefined) {
      throw new SatRootError(`missing required field: ${f}`);
    }
  }
}

function validateStatedEventId(event: Event): void {
  const stated = event["event_id"];
  if (stated !== undefined && stated !== null && stated !== eventId(event)) {
    throw new SatRootError("event_id mismatch");
  }
}

function validateStateHash(event: Event, s: State): void {
  const stated = event["state_hash"];
  if (stated !== undefined && stated !== null && stated !== stateHash(s)) {
    throw new SatRootError("state_hash mismatch");
  }
}

const SCHEMES = ["demo", "hmac-sha256", "ed25519"];

function validateSignatureMetadata(event: Event): void {
  const scheme = (event["signature_scheme"] ?? "demo") as string;
  if (typeof scheme !== "string" || !SCHEMES.includes(scheme)) {
    throw new SatRootError(`unsupported signature_scheme: ${String(scheme)}`);
  }
  const keyId = event["signature_key_id"];
  if (scheme === "demo") {
    if (keyId !== undefined && keyId !== null) {
      throw new SatRootError("signature_key_id is not allowed for demo signatures");
    }
    return;
  }
  if (typeof keyId !== "string" || keyId.trim() === "") {
    throw new SatRootError(`signature_key_id is required for ${scheme}`);
  }
}

/* ------------------------------------------------------------------ */
/* Replay                                                              */
/* ------------------------------------------------------------------ */

function applyGenesis(event: Event): State {
  requireFields(event, [
    "protocol", "version", "action", "root_id", "sequence", "symbol", "name",
    "decimals", "max_supply", "mint_authority", "initial_balances",
  ]);
  if (event["protocol"] !== "SATROOT-1" || event["version"] !== "0.1") {
    throw new SatRootError("unsupported protocol/version");
  }
  if (event["action"] !== "genesis") throw new SatRootError("first event must be genesis");
  if (typeof event["sequence"] !== "number" || event["sequence"] !== 0) {
    throw new SatRootError("genesis sequence must be 0");
  }
  if (typeof event["root_id"] !== "string" || !/^[0-9a-f]{64}:\d+$/.test(event["root_id"])) {
    throw new SatRootError("invalid root_id");
  }
  validateStatedEventId(event);
  if (event["transfer_model"] !== "account-ledger") {
    throw new SatRootError("unsupported transfer_model");
  }

  const rawBalances = event["initial_balances"];
  if (rawBalances === null || typeof rawBalances !== "object" || Array.isArray(rawBalances)) {
    throw new SatRootError("initial_balances must be an object");
  }
  const balances = new Map<string, bigint>();
  let supply = 0n;
  for (const [acct, amount] of Object.entries(rawBalances as { [k: string]: Json })) {
    const value = parseAmount(amount);
    balances.set(accountName(acct, "initial_balances"), value);
    supply += value;
  }
  const maxSupply = event["max_supply"] === null ? null : parseAmount(event["max_supply"]);
  if (maxSupply !== null && supply > maxSupply) {
    throw new SatRootError("initial supply exceeds max supply");
  }

  const state: State = {
    rootId: event["root_id"] as string,
    symbol: event["symbol"] as string,
    name: event["name"] as string,
    decimals: parseDecimals(event["decimals"]),
    maxSupply,
    mintAuthority: event["mint_authority"] as string,
    profile: (event["profile"] ?? null) as Json,
    profileMode: (event["profile_mode"] ?? null) as Json,
    balances,
    frozen: new Set<string>(),
    supply,
    sequence: 0,
    lastEventId: eventId(event),
  };
  validateStateHash(event, state);
  return state;
}

function cloneState(s: State): State {
  return { ...s, balances: new Map(s.balances), frozen: new Set(s.frozen) };
}

function applyEvent(prev: State, event: Event, verifier: Verifier): State {
  const s = cloneState(prev);

  requireFields(event, [
    "protocol", "version", "action", "root_id", "sequence",
    "prev_event_id", "signer", "signature",
  ]);
  if (event["protocol"] !== "SATROOT-1" || event["version"] !== "0.1") {
    throw new SatRootError("unsupported protocol/version");
  }
  if (event["root_id"] !== s.rootId) throw new SatRootError("root_id mismatch");
  if (typeof event["sequence"] !== "number" || event["sequence"] !== s.sequence + 1) {
    throw new SatRootError("bad sequence");
  }
  if (event["prev_event_id"] !== s.lastEventId) throw new SatRootError("bad prev_event_id");
  validateStatedEventId(event);
  validateSignatureMetadata(event);
  const evProfile = event["profile"];
  if (evProfile !== undefined && evProfile !== null && evProfile !== s.profile) {
    throw new SatRootError("profile mismatch");
  }
  const evMode = event["profile_mode"];
  if (evMode !== undefined && evMode !== null && evMode !== s.profileMode) {
    throw new SatRootError("profile_mode mismatch");
  }
  if (!verifier(event, signingPayload(event))) {
    throw new SatRootError("signature verification failed");
  }

  const action = event["action"];
  const get = (a: string) => s.balances.get(a) ?? 0n;

  if (action === "mint") {
    requireFields(event, ["to", "amount"]);
    const amount = parsePositiveAmount(event["amount"]);
    if (event["signer"] !== s.mintAuthority) throw new SatRootError("unauthorized mint");
    const to = accountName(event["to"], "to");
    if (s.frozen.has(to)) throw new SatRootError("account is frozen");
    if (s.maxSupply !== null && s.supply + amount > s.maxSupply) {
      throw new SatRootError("mint exceeds max supply");
    }
    s.balances.set(to, get(to) + amount);
    s.supply += amount;
  } else if (action === "transfer") {
    requireFields(event, ["from", "to", "amount"]);
    const amount = parsePositiveAmount(event["amount"]);
    const sender = accountName(event["from"], "from");
    const recipient = accountName(event["to"], "to");
    if (event["signer"] !== sender) throw new SatRootError("unauthorized transfer");
    if (s.frozen.has(sender) || s.frozen.has(recipient)) {
      throw new SatRootError("account is frozen");
    }
    if (get(sender) < amount) throw new SatRootError("insufficient balance");
    s.balances.set(sender, get(sender) - amount);
    s.balances.set(recipient, get(recipient) + amount);
  } else if (action === "burn") {
    requireFields(event, ["from", "amount"]);
    const amount = parsePositiveAmount(event["amount"]);
    const burner = accountName(event["from"], "from");
    if (event["signer"] !== burner) throw new SatRootError("unauthorized burn");
    if (s.frozen.has(burner)) throw new SatRootError("account is frozen");
    if (get(burner) < amount) throw new SatRootError("insufficient balance");
    s.balances.set(burner, get(burner) - amount);
    s.supply -= amount;
  } else if (action === "freeze") {
    requireFields(event, ["account", "frozen"]);
    if (event["signer"] !== s.mintAuthority) throw new SatRootError("unauthorized freeze");
    const account = accountName(event["account"], "account");
    const frozen = event["frozen"];
    if (typeof frozen !== "boolean") {
      throw new SatRootError("freeze event frozen must be a boolean");
    }
    if (frozen) s.frozen.add(account);
    else s.frozen.delete(account);
  } else if (action === "rotate-authority") {
    requireFields(event, ["new_mint_authority"]);
    if (event["signer"] !== s.mintAuthority) {
      throw new SatRootError("unauthorized authority rotation");
    }
    s.mintAuthority = accountName(event["new_mint_authority"], "new_mint_authority");
  } else {
    throw new SatRootError(`unsupported action: ${String(action)}`);
  }

  s.sequence = event["sequence"] as number;
  s.lastEventId = eventId(event);
  validateStateHash(event, s);
  return s;
}

/** Replay a full ledger. Throws SatRootError on any rule violation. */
export function replay(events: Event[], verifier: Verifier = demoVerifier): State {
  if (events.length === 0) throw new SatRootError("empty ledger");
  let state = applyGenesis(events[0]);
  for (const event of events.slice(1)) {
    if (event["action"] === "genesis") throw new SatRootError("duplicate genesis");
    state = applyEvent(state, event, verifier);
  }
  return state;
}
