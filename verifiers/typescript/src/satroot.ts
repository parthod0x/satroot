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
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

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
  // SPEC.md section 2.6: keys sort by Unicode code point. Array.sort compares
  // UTF-16 code units, which orders U+E000 after U+1F600 - the opposite of
  // every code-point sort - so two astral account names hashed differently.
  const keys = Object.keys(value).sort(compareCodePoints);
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
}

/** Order two strings by Unicode code point, as SPEC.md section 2.6 requires. */
export function compareCodePoints(a: string, b: string): number {
  const ia = a[Symbol.iterator]();
  const ib = b[Symbol.iterator]();
  for (;;) {
    const x = ia.next();
    const y = ib.next();
    if (x.done) return y.done ? 0 : -1;
    if (y.done) return 1;
    const cx = x.value.codePointAt(0)!;
    const cy = y.value.codePointAt(0)!;
    if (cx !== cy) return cx < cy ? -1 : 1;
  }
}

/** An object with no prototype, so a member named __proto__ is just a member. */
function bare<T>(): { [k: string]: T } {
  return Object.create(null) as { [k: string]: T };
}

function own<T>(map: { [k: string]: T }, key: string): T | undefined {
  return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : undefined;
}

export function sha256Hex(data: string): string {
  return createHash("sha256").update(Buffer.from(data, "utf8")).digest("hex");
}

function omit(event: Event, drop: string[]): Event {
  const out: Event = bare<Json>();
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
/* Input profile - SPEC.md section 2.6a                                */
/* ------------------------------------------------------------------ */

/**
 * Parse ledger JSON under the input profile. JSON.parse cannot be used: it
 * reads 2.0 as 2, keeps the last of two duplicate members, rounds integers
 * past 2^53, and gives an object member named __proto__ special meaning -
 * each a way to read a different ledger from the same text than another
 * implementation does. Numbers must be integers with no fraction or exponent,
 * within +/-(2^53 - 1); member names must be unique; strings must not hold a
 * lone surrogate. Objects come back without a prototype.
 */
/** Deepest nesting of arrays and objects a record may hold (SPEC.md 2.6a). */
export const MAX_NESTING_DEPTH = 64;

export function parseLedgerJson(text: string): Json {
  let i = 0;
  let depth = 0;
  const fail = (why: string): never => {
    throw new SatRootError(`input profile: ${why} at offset ${i}`);
  };
  const ws = () => {
    while (i < text.length && " \t\n\r".includes(text[i])) i++;
  };
  const value = (): Json => {
    ws();
    const c = text[i];
    if ((c === "{" || c === "[") && ++depth > MAX_NESTING_DEPTH) fail("nesting deeper than " + MAX_NESTING_DEPTH);
    if (c === "{") {
      i++;
      const out = bare<Json>();
      ws();
      if (text[i] === "}") { i++; depth--; return out; }
      for (;;) {
        ws();
        if (text[i] !== '"') fail("expected a member name");
        const key = str();
        if (Object.prototype.hasOwnProperty.call(out, key)) fail(`duplicate member name ${JSON.stringify(key)}`);
        ws();
        if (text[i++] !== ":") fail("expected ':'");
        out[key] = value();
        ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "}") { i++; depth--; return out; }
        fail("expected ',' or '}'");
      }
    }
    if (c === "[") {
      i++;
      const out: Json[] = [];
      ws();
      if (text[i] === "]") { i++; depth--; return out; }
      for (;;) {
        out.push(value());
        ws();
        if (text[i] === ",") { i++; continue; }
        if (text[i] === "]") { i++; depth--; return out; }
        fail("expected ',' or ']'");
      }
    }
    if (c === '"') return str();
    if (text.startsWith("true", i)) { i += 4; return true; }
    if (text.startsWith("false", i)) { i += 5; return false; }
    if (text.startsWith("null", i)) { i += 4; return null; }
    const m = /^-?(0|[1-9][0-9]*)([.eE][-+0-9.eE]*)?/.exec(text.slice(i));
    if (m === null) return fail("unexpected input");
    if (m[2] !== undefined) fail("non-integer number " + m[0]);
    const n = Number(m[0]);
    if (!Number.isSafeInteger(n)) fail("integer beyond 2^53 - 1");
    i += m[0].length;
    return n;
  };
  const str = (): string => {
    i++; // opening quote
    let out = "";
    for (;;) {
      if (i >= text.length) fail("unterminated string");
      const c = text[i++];
      if (c === '"') break;
      if (c === "\\") {
        const e = text[i++];
        const simple: { [k: string]: string } = { '"': '"', "\\": "\\", "/": "/", b: "\b", f: "\f", n: "\n", r: "\r", t: "\t" };
        if (e === "u") {
          const hex = text.slice(i, i + 4);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) fail("bad \\u escape");
          out += String.fromCharCode(parseInt(hex, 16));
          i += 4;
        } else if (e in simple) {
          out += simple[e];
        } else {
          fail("bad escape");
        }
      } else {
        if (c < " ") fail("unescaped control character in string");
        out += c;
      }
    }
    if (hasLoneSurrogate(out)) fail("lone surrogate in string");
    return out;
  };
  const result = value();
  ws();
  if (i !== text.length) fail("trailing data");
  return result;
}

function hasLoneSurrogate(value: string): boolean {
  for (let k = 0; k < value.length; k++) {
    const u = value.charCodeAt(k);
    if (u >= 0xd800 && u <= 0xdbff) {
      const next = value.charCodeAt(k + 1);
      if (next >= 0xdc00 && next <= 0xdfff) { k++; continue; }
      return true;
    }
    if (u >= 0xdc00 && u <= 0xdfff) return true;
  }
  return false;
}

/** The same profile, checked on values already parsed (SPEC.md section 2.6a). */
function checkInputProfile(value: Json, where: string, depth = 0): void {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "object" && depth >= MAX_NESTING_DEPTH) {
    throw new SatRootError(`input profile: ${where} nests deeper than ${MAX_NESTING_DEPTH}`);
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) throw new SatRootError(`input profile: ${where} holds a non-integer or unsafe number`);
    return;
  }
  if (typeof value === "string") {
    if (hasLoneSurrogate(value)) throw new SatRootError(`input profile: ${where} holds a lone surrogate`);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) checkInputProfile(item, where, depth + 1);
    return;
  }
  for (const key of Object.keys(value)) {
    if (hasLoneSurrogate(key)) throw new SatRootError(`input profile: ${where} holds a lone surrogate`);
    checkInputProfile(value[key], where, depth + 1);
  }
}

/** Characters that make a name blank when it consists only of them. */
const NAME_BLANK = new Set([0x20, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,
  0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000]);

/**
 * A name (account or key id): non-empty, no control character (C0, DEL, C1),
 * no byte-order mark, no lone surrogate, and not made only of NAME_BLANK.
 * Explicit because String.trim and Python's str.strip disagree on U+001C,
 * U+0085 and U+FEFF. SPEC.md section 2.6a.
 */
export function isValidName(value: Json): boolean {
  if (typeof value !== "string" || value === "" || hasLoneSurrogate(value)) return false;
  let substantive = false;
  for (const ch of value) {
    const cp = ch.codePointAt(0)!;
    if (cp < 0x20 || (cp >= 0x7f && cp <= 0x9f) || cp === 0xfeff) return false;
    if (!NAME_BLANK.has(cp)) substantive = true;
  }
  return substantive;
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
    const secret = own(secrets, keyId);
    if (typeof secret !== "string") return false;
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
    const pubHex = own(publicKeys, keyId);
    const signature = event["signature"];
    if (typeof pubHex !== "string" || typeof signature !== "string") return false;
    // Exact encodings: Buffer.from(hex) stops at the first bad character, so
    // trailing junk or an odd nibble decoded to a valid signature.
    if (!/^ed25519:[0-9a-f]{128}$/.test(signature) || !/^[0-9a-f]{64}$/.test(pubHex)) return false;
    try {
      const sig = Buffer.from(signature.slice("ed25519:".length), "hex");
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
  version: string;
  accountKeys: Map<string, string>;
}

export const LEDGER_VERSION_UNBOUND = "0.1";
export const LEDGER_VERSION_BOUND = "0.2";

/** The commitment snapshot the state hash is taken over. */
export function commitmentSnapshot(s: State): Json {
  const balances = bare<Json>();
  for (const acct of [...s.balances.keys()].sort(compareCodePoints)) {
    const v = s.balances.get(acct)!;
    if (v !== 0n) balances[acct] = v.toString();
  }
  const snapshot: { [k: string]: Json } = {
    root_id: s.rootId,
    symbol: s.symbol,
    name: s.name,
    decimals: s.decimals,
    max_supply: s.maxSupply === null ? null : s.maxSupply.toString(),
    mint_authority: s.mintAuthority,
    profile: s.profile ?? null,
    profile_mode: s.profileMode ?? null,
    balances,
    frozen_accounts: [...s.frozen].sort(compareCodePoints),
    supply: s.supply.toString(),
    sequence: s.sequence,
    last_event_id: s.lastEventId,
  };
  if (s.version === LEDGER_VERSION_BOUND) {
    const keys = bare<Json>();
    for (const acct of [...s.accountKeys.keys()].sort(compareCodePoints)) keys[acct] = s.accountKeys.get(acct)!;
    snapshot["account_keys"] = keys;
  }
  return snapshot;
}

export function stateHash(s: State): string {
  return "sha256:" + sha256Hex(canonicalJson(commitmentSnapshot(s)));
}

/* ------------------------------------------------------------------ */
/* Field parsing                                                       */
/* ------------------------------------------------------------------ */

const AMOUNT_RE = /^[0-9]+$/;

/**
 * Maximum digits in any protocol amount. BigInt itself is unbounded, so
 * this bound exists purely to keep the accept/reject decision identical
 * to every other implementation — see SPEC.md.
 */
export const MAX_AMOUNT_DIGITS = 512;

function parseAmount(value: Json): bigint {
  if (typeof value !== "string" || !AMOUNT_RE.test(value)) {
    throw new SatRootError(`invalid amount: ${JSON.stringify(value)}`);
  }
  if (value.length > MAX_AMOUNT_DIGITS) {
    throw new SatRootError(`amount exceeds ${MAX_AMOUNT_DIGITS} digits`);
  }
  // Canonical form only - SPEC.md section 6.1a. This verifier had the same
  // gap as the Python reference, and for the same reason: the vector that
  // was supposed to test it was decided by a stale event_id instead.
  if (value.length > 1 && value[0] === "0") {
    throw new SatRootError(`amount has a leading zero: ${JSON.stringify(value)}`);
  }
  return BigInt(value);
}

function parsePositiveAmount(value: Json): bigint {
  const amount = parseAmount(value);
  if (amount <= 0n) throw new SatRootError("amount must be positive");
  return amount;
}

function accountName(value: Json, field: string): string {
  if (!isValidName(value)) throw new SatRootError(`invalid account name for ${field}`);
  return value as string;
}

function keyIdName(value: Json, field: string): string {
  if (!isValidName(value)) throw new SatRootError(`invalid key id for ${field}`);
  return value as string;
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

function schemeOf(event: Event): Json {
  // Absent means demo; present must be one of the schemes. `?? "demo"` read
  // an explicit null as demo, which the reference rejects.
  return Object.prototype.hasOwnProperty.call(event, "signature_scheme") ? event["signature_scheme"] : "demo";
}

function validateSignatureMetadata(event: Event): void {
  const scheme = schemeOf(event);
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
  if (!isValidName(keyId)) {
    throw new SatRootError(`signature_key_id is required for ${scheme}`);
  }
}

function requireBoundKey(accountKeys: Map<string, string>, signer: Json, event: Event): void {
  const bound = typeof signer === "string" ? accountKeys.get(signer) : undefined;
  if (bound === undefined) throw new SatRootError(`signer has no bound key`);
  if (event["signature_key_id"] !== bound) throw new SatRootError(`event is not signed by its signer's bound key`);
}

export interface ReplayOptions {
  /** Admit a version-0.1 ledger under a real scheme: its keys are bound to no account. */
  allowUnboundKeys?: boolean;
  /** The genesis event id kept from an earlier copy or an anchor (SPEC.md section 6.7). */
  expectedGenesisEventId?: string;
}

/* ------------------------------------------------------------------ */
/* Replay                                                              */
/* ------------------------------------------------------------------ */

/**
 * Registry-level profile rules - SPEC.md section 8.10.
 *
 * This verifier accepted any profile at all until the conformance corpus
 * grew vectors for it, because the committed profile/profile_mode members
 * were always null and nothing exercised the registry. Scope note: the
 * registry-level rules are implemented here (known profile, the mode the
 * registry pairs with it, required genesis fields present and non-empty).
 * The per-profile semantic constraints the reference also enforces are not,
 * and no vector currently distinguishes them.
 */
interface ProfileRules {
  profile_mode: string;
  required_genesis_fields: string[];
}

let profileRegistry: Map<string, ProfileRules> | null = null;

function loadProfileRegistry(): Map<string, ProfileRules> {
  if (profileRegistry !== null) return profileRegistry;
  const here = dirname(fileURLToPath(import.meta.url));
  const path = join(here, "..", "..", "..", "protocol", "satroot1.profile-registry.json");
  const raw = JSON.parse(readFileSync(path, "utf8")) as {
    protocol?: string;
    version?: string;
    profiles?: Array<ProfileRules & { profile: string }>;
  };
  if (raw.protocol !== "SATROOT-1" || raw.version !== "0.1") {
    throw new SatRootError("unsupported profile registry version");
  }
  const out = new Map<string, ProfileRules>();
  for (const entry of raw.profiles ?? []) out.set(entry.profile, entry);
  profileRegistry = out;
  return out;
}

function validateProfileGenesis(event: Event): void {
  const profile = event["profile"];
  if (profile === undefined || profile === null) {
    // An orphan profile_mode was validated against nothing and committed
    // verbatim by section 7, so arbitrary JSON reached the state hash.
    const orphan = event["profile_mode"];
    if (orphan !== undefined && orphan !== null) {
      throw new SatRootError("profile_mode requires a profile");
    }
    return;
  }
  if (typeof profile !== "string") throw new SatRootError("invalid profile");

  const rules = loadProfileRegistry().get(profile);
  if (rules === undefined) throw new SatRootError(`unsupported profile: ${profile}`);

  const needed = ["profile_mode", ...rules.required_genesis_fields];
  requireFields(event, needed);
  if (event["profile_mode"] !== rules.profile_mode) {
    throw new SatRootError(`bad profile_mode for ${profile}`);
  }
  for (const field of needed) {
    // The name rule of SPEC.md section 2.6a, not String.trim.
    if (!isValidName(event[field])) {
      throw new SatRootError(`invalid profile field ${field}: expected a non-blank string`);
    }
  }
  validateProfileSpecificGenesis(profile, event);
}

/* Per-profile rules, as the reference applies them (SPEC.md section 5.2).
 * This verifier used to stop at the registry-level rules, so it accepted a
 * stable profile with reference_unit "usd" or a receipt profile issuing two
 * units, both of which the reference rejects. */
const REFERENCE_UNIT_RE = /^[A-Z0-9][A-Z0-9._-]{1,15}$/;
const COMPACT_IDENTIFIER_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/;

function compactField(event: Event, field: string): void {
  if (!COMPACT_IDENTIFIER_RE.test(event[field] as string)) {
    throw new SatRootError(`invalid profile field ${field}: expected compact identifier`);
  }
}

function singletonObject(event: Event, label: string): void {
  if (parseDecimals(event["decimals"]) !== 0) throw new SatRootError(`${label} profile requires decimals=0`);
  if (parseAmount(event["max_supply"]) !== 1n) throw new SatRootError(`${label} profile requires max_supply=1`);
  const balances = event["initial_balances"];
  if (balances === null || typeof balances !== "object" || Array.isArray(balances)) {
    throw new SatRootError(`${label} profile initial_balances must be an object`);
  }
  let total = 0n;
  for (const acct of Object.keys(balances)) total += parseAmount((balances as { [k: string]: Json })[acct]);
  if (total !== 1n) throw new SatRootError(`${label} profile requires exactly one issued unit at genesis`);
}

function validateProfileSpecificGenesis(profile: string, event: Event): void {
  if (profile === "SATROOT-STABLE-1") {
    if (!REFERENCE_UNIT_RE.test(event["reference_unit"] as string)) throw new SatRootError("invalid stable reference_unit");
    if (event["profile_mode"] === "reference-only") {
      if (event["redemption"] !== "none") throw new SatRootError("reference-only stable profile requires redemption=none");
      if (event["reserve_model"] !== "none") throw new SatRootError("reference-only stable profile requires reserve_model=none");
    }
  } else if (profile === "SATROOT-MACHINE-1") {
    for (const f of ["service_scope", "billing_unit", "consumption_model", "intended_use"]) compactField(event, f);
  } else if (profile === "SATROOT-RECEIPT-1") {
    compactField(event, "document_type");
    compactField(event, "intended_use");
    if (!REFERENCE_UNIT_RE.test(event["settlement_unit"] as string)) throw new SatRootError("invalid receipt settlement_unit");
    singletonObject(event, "receipt");
  } else if (profile === "SATROOT-IDENTITY-1") {
    for (const f of ["identity_type", "authority_scope", "intended_use"]) compactField(event, f);
    singletonObject(event, "identity");
  } else if (profile === "SATROOT-LICENSE-1") {
    for (const f of ["license_type", "usage_scope", "intended_use"]) compactField(event, f);
    singletonObject(event, "license");
  } else if (profile === "SATROOT-EVENT-1") {
    for (const f of ["stream_type", "sequence_policy", "intended_use"]) compactField(event, f);
    singletonObject(event, "event-stream");
  }
}

function applyGenesis(event: Event, verifier: Verifier = demoVerifier, options: ReplayOptions = {}): State {
  checkInputProfile(event, "genesis");
  requireFields(event, [
    "protocol", "version", "action", "root_id", "sequence", "symbol", "name",
    "decimals", "max_supply", "mint_authority", "initial_balances",
    "signature",
  ]);
  const version = event["version"];
  if (event["protocol"] !== "SATROOT-1" || (version !== LEDGER_VERSION_UNBOUND && version !== LEDGER_VERSION_BOUND)) {
    throw new SatRootError("unsupported protocol/version");
  }
  if (event["action"] !== "genesis") throw new SatRootError("first event must be genesis");
  if (typeof event["sequence"] !== "number" || event["sequence"] !== 0) {
    throw new SatRootError("genesis sequence must be 0");
  }
  if (typeof event["root_id"] !== "string" || !/^[0-9a-f]{64}:(0|[1-9][0-9]{0,9})$/.test(event["root_id"])) {
    throw new SatRootError("invalid root_id");
  }
  validateStatedEventId(event);
  // Genesis fixes mint_authority, max_supply and the whole initial
  // allocation, and this verifier never authenticated it - applyGenesis
  // took no verifier at all, exactly as the Python reference did. Two
  // implementations with the same hole, because SPEC.md scoped its
  // signature requirement to non-genesis events. See SPEC.md section 5.
  validateSignatureMetadata(event);
  const scheme = schemeOf(event);
  const accountKeys = new Map<string, string>();
  if (version === LEDGER_VERSION_BOUND) {
    const raw = event["account_keys"];
    if (raw !== undefined || scheme !== "demo") {
      if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
        throw new SatRootError("account_keys must be an object mapping account -> key id");
      }
      for (const acct of Object.keys(raw)) {
        accountKeys.set(accountName(acct, "account_keys"), keyIdName((raw as { [k: string]: Json })[acct], "account_keys"));
      }
    }
    // Genesis has no signer: it is signed by the authority it appoints.
    if (scheme !== "demo") requireBoundKey(accountKeys, event["mint_authority"], event);
  } else {
    if (Object.prototype.hasOwnProperty.call(event, "account_keys")) {
      throw new SatRootError("account_keys requires ledger version 0.2");
    }
    if (scheme !== "demo" && !options.allowUnboundKeys) {
      throw new SatRootError("ledger version 0.1 binds no signing key to any account");
    }
  }
  if (!verifier(event, signingPayload(event))) {
    throw new SatRootError("signature verification failed");
  }
  validateProfileGenesis(event);
  if (event["transfer_model"] !== "account-ledger") {
    throw new SatRootError("unsupported transfer_model");
  }
  accountName(event["mint_authority"], "mint_authority");
  if (typeof event["symbol"] !== "string" || typeof event["name"] !== "string") {
    throw new SatRootError("genesis symbol and name must be strings");
  }

  const rawBalances = event["initial_balances"];
  if (rawBalances === null || typeof rawBalances !== "object" || Array.isArray(rawBalances)) {
    throw new SatRootError("initial_balances must be an object");
  }
  const balances = new Map<string, bigint>();
  let supply = 0n;
  for (const acct of Object.keys(rawBalances)) {
    const amount = (rawBalances as { [k: string]: Json })[acct];
    const value = parseAmount(amount);
    balances.set(accountName(acct, "initial_balances"), value);
    supply += value;
  }
  if (version === LEDGER_VERSION_BOUND && scheme !== "demo") {
    // Value sits only where a key can move it (SPEC.md 6.7).
    for (const [acct, amount] of balances) {
      if (amount !== 0n && !accountKeys.has(acct)) throw new SatRootError("genesis credits an account with no bound key");
    }
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
    version: version as string,
    accountKeys,
  };
  validateStateHash(event, state);
  return state;
}

function cloneState(s: State): State {
  return { ...s, balances: new Map(s.balances), frozen: new Set(s.frozen), accountKeys: new Map(s.accountKeys) };
}

function applyEvent(prev: State, event: Event, verifier: Verifier): State {
  const s = cloneState(prev);
  checkInputProfile(event, "event");

  requireFields(event, [
    "protocol", "version", "action", "root_id", "sequence",
    "prev_event_id", "signer", "signature",
  ]);
  if (event["protocol"] !== "SATROOT-1" || (event["version"] !== LEDGER_VERSION_UNBOUND && event["version"] !== LEDGER_VERSION_BOUND)) {
    throw new SatRootError("unsupported protocol/version");
  }
  if (event["version"] !== s.version) throw new SatRootError("ledger version mismatch");
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
  const bound = s.version === LEDGER_VERSION_BOUND && schemeOf(event) !== "demo";
  if (bound) requireBoundKey(s.accountKeys, event["signer"], event);
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
    if (bound && !s.accountKeys.has(to)) throw new SatRootError("recipient has no bound key");
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
    if (bound && !s.accountKeys.has(recipient)) throw new SatRootError("recipient has no bound key");
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
    const newAuthority = accountName(event["new_mint_authority"], "new_mint_authority");
    if (bound && !s.accountKeys.has(newAuthority)) throw new SatRootError("new mint authority has no bound key");
    s.mintAuthority = newAuthority;
  } else if (action === "bind-key" && s.version === LEDGER_VERSION_BOUND) {
    requireFields(event, ["account", "key_id"]);
    const account = accountName(event["account"], "account");
    const keyId = keyIdName(event["key_id"], "key_id");
    if (s.accountKeys.has(account)) {
      if (event["signer"] !== account) throw new SatRootError("only the account can rebind its own key");
    } else if (event["signer"] !== s.mintAuthority) {
      throw new SatRootError("unauthorized key binding");
    }
    s.accountKeys.set(account, keyId);
  } else {
    throw new SatRootError(`unsupported action: ${String(action)}`);
  }

  s.sequence = event["sequence"] as number;
  s.lastEventId = eventId(event);
  validateStateHash(event, s);
  return s;
}

/** Replay a full ledger. Throws SatRootError on any rule violation. */
export function replay(events: Event[], verifier: Verifier = demoVerifier, options: ReplayOptions = {}): State {
  if (!Array.isArray(events) || events.length === 0) throw new SatRootError("empty ledger");
  for (const event of events) {
    if (event === null || typeof event !== "object" || Array.isArray(event)) throw new SatRootError("event must be an object");
  }
  let state = applyGenesis(events[0], verifier, options);
  if (options.expectedGenesisEventId !== undefined && state.lastEventId !== options.expectedGenesisEventId) {
    throw new SatRootError("genesis does not match the pinned genesis event id");
  }
  for (const event of events.slice(1)) {
    if (event["action"] === "genesis") throw new SatRootError("duplicate genesis");
    state = applyEvent(state, event, verifier);
  }
  return state;
}
