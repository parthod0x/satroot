# SATROOT-1 Specification

Status: v1 draft (frozen at v1.0-draft-freeze)
Date: 2026-08-19
License: Apache-2.0

## 1. Purpose

SATROOT-1 defines a minimal token primitive in which a single native satoshi UTXO acts as the root witness and authority handle for an arbitrary higher-layer token ledger.

It is designed to make one idea precise:

> There is no smaller Bitcoin unit below one satoshi, but there can be unbounded protocol-defined semantic state above one satoshi.

Within the broader SATROOT project, this base primitive should also be understood as a root-bound namespace kernel. The root satoshi does not merely anchor one token balance. It anchors a deterministic protocol namespace under which semantic objects can later exist.

## 2. Core concepts

### 2.1 Root satoshi

A **root satoshi** is a UTXO with native value exactly `1 satoshi`.

The root satoshi is not divided. It is used as a carrier, anchor, authority witness, or namespace handle.

### 2.2 Root ID

The **root_id** is the outpoint of the root satoshi:

```text
<genesis_txid>:<vout>
```

This root_id identifies the token universe.

### 2.3 Semantic supply

The token supply is not native Bitcoin supply. It is semantic supply defined by protocol records.

A SATROOT-1 token can have:

- fixed supply,
- capped minting,
- uncapped minting,
- authority-controlled minting,
- no further minting after genesis.

### 2.4 Root-bound namespace

The deeper SATROOT model is:

```text
1 satoshi -> 1 root namespace -> many semantic objects
```

In `SATROOT-1`, that namespace is used only for a token ledger. Registered profiles already use the same root structure for receipts, credits, licenses, identities, machine-readable rights, and event-stream heads.

### 2.5 Event ledger

Token balances are computed by replaying signed SATROOT-1 events:

- `genesis`
- `mint`
- `transfer`
- `burn`
- `rotate-authority`
- `freeze`
- `delegate` optional in future versions

Every non-genesis event must reference:

- `root_id`
- `prev_event_id`
- `sequence`
- `action`
- action-specific fields such as `from`, `to`, and `amount`
- `signer`
- `signature`

When present, `signature_scheme` and `signature_key_id` describe how the signature should be interpreted.

The canonical signing payload is the canonical JSON form of the event excluding:

- `signature`
- `event_id`
- `state_hash`

This keeps the signed content stable while allowing transport metadata and post-application state commitments to be attached separately.

The payload may still include fields such as `signature_scheme` or `signature_key_id` when those fields are part of the verification model in use.

Known profiles and their required genesis metadata are listed in `protocol/satroot1.profile-registry.json`. Strict SATROOT-1 replay engines should treat that registry as the compatibility source of truth and reject unknown profiles until explicitly supported.

When a profile draft defines explicit safe-mode guardrails, replay engines may also enforce those genesis metadata constraints directly. For example, a `SATROOT-STABLE-1` `reference-only` genesis may require `redemption=none` and `reserve_model=none` so the ledger cannot accidentally claim redeemability or reserves while still presenting itself as reference-only.

Likewise, machine and single-object profiles may enforce compact identifier formatting for fields such as `service_scope`, `document_type`, `identity_type`, `license_type`, and related usage metadata, while `single-receipt`, `single-identity`, and `single-license` modes may require a zero-decimal, one-unit genesis so the ledger unambiguously anchors one object.

### 2.6 Canonical JSON

Every hash and every signature in this specification is taken over
*canonical JSON*. Two implementations that disagree on this serialisation
will disagree on every event id, state hash and signature, so it is defined
exactly:

- **Object keys are sorted** by Unicode code point, at every level of nesting.
- **No insignificant whitespace.** The separator between a key and its value
  is `:` and between members is `,`, with no spaces.
- **Non-ASCII characters are emitted raw**, as UTF-8, not as `\uXXXX`
  escapes. Characters that JSON requires to be escaped are still escaped.
- **The result is encoded as UTF-8** before hashing or signing.

Equivalent to Python's
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.

Protocol amounts, balances and supply values are carried as **digit
strings**, not JSON numbers, so serialisation never depends on a language's
floating-point or big-integer formatting. See section 6.1a.

### 2.7 Event identity

The event id is the canonical hash of the record with `event_id` and
`state_hash` removed:

```text
event_id = "sha256:" + hex(sha256(canonical_json(event - {event_id, state_hash})))
```

The `sha256:` prefix is part of the value. Hex digits are lowercase.

The **signing payload** is the same construction with `signature` also
removed, and is *not* hashed before signing - it is the canonical JSON
string itself, UTF-8 encoded:

```text
signing_payload = canonical_json(event - {signature, event_id, state_hash})
```

## 3. Boundary rule

A SATROOT-1 event MUST NOT claim that tokens are sub-satoshis.

Correct:

```text
1 root satoshi anchors 1,000,000,000 FLOOR1 units.
```

Incorrect:

```text
1 satoshi is divided into 1,000,000,000 smaller satoshis.
```

## 4. Recommended on-chain envelope

The minimal payload may be placed in an unspendable data output, while the root satoshi remains in a spendable 1-satoshi output.

Recommended envelope:

```text
OP_FALSE OP_RETURN "SATROOT1" <content-type> <payload-bytes>
```

Recommended content type:

```text
application/satroot1+json
```

For larger systems, the payload may be replaced by a content hash and an external availability pointer.

A deterministic offline builder and an offline raw-transaction verifier for this envelope are released with the reference implementation; one broadcast envelope carrying a real anchored-namespace state commitment is recorded in `ANCHORS.md`.

## 5. Genesis record

A genesis record defines the token universe.

Required fields — all of the following, and `sequence`, which MUST be `0`:

```json
{
  "protocol": "SATROOT-1",
  "version": "0.1",
  "action": "genesis",
  "root_id": "<txid>:<vout>",
  "symbol": "FLOOR1",
  "name": "One Satoshi Floor Token",
  "decimals": 0,
  "max_supply": "1000000000",
  "mint_authority": "issuer_pubkey_or_script_hash",
  "transfer_model": "account-ledger",
  "initial_balances": {
    "issuer": "1000000000"
  }
}
```

`decimals` MUST be a non-negative JSON integer. A JSON boolean is not an
integer for this purpose, even in languages where `true` compares equal to
`1`.

`rules_hash` and `nonce` are OPTIONAL. Earlier revisions of this section
listed them among the required fields; no conforming ledger has ever carried
either, and an implementation that required them would reject every valid
ledger in existence.

### 5.1 Genesis MUST be signed

**A genesis record carries `signature`, and a conforming implementation MUST
verify it with the same verifier and the same rules it applies to every
other event (sections 2.7 and 6.6).** A genesis whose signature is absent,
empty, forged, or made under a scheme the verifier does not accept is
rejected.

Its signature metadata follows section 6.6.1 exactly as a non-genesis event
does:

- `signature_scheme` is OPTIONAL and defaults to `demo` when absent, by the
  universal rule in section 6.6.1 — this is not a genesis-specific default.
  The conformance corpus carries both forms: genesis records that state
  `"signature_scheme": "demo"` explicitly, and one that relies on the
  implicit default. Both are valid, and they are different records with
  different `event_id` values.
- `signature_key_id` is REQUIRED for `hmac-sha256` and `ed25519`, and MUST
  be absent for `demo`.

An earlier revision of this paragraph said a genesis carries
`signature_scheme` "where the scheme is not `demo`", which read as though a
demo genesis must omit it while every vector in the then-current corpus
carried one.

Genesis does not carry `signer`; the signing key is identified by
`signature_key_id` under the real schemes, and `demo` records carry neither.

This is stated because the earlier text did not state it, and the omission
was load-bearing. Section 2.5 lists `signer` and `signature` among the
fields "every non-genesis event must reference", and section 5's field list
named neither — so nothing in this document ever said a genesis was
authenticated, while section 8.7 rejects when "a required signature check
fails" and every genesis in the conformance corpus carries a `signature`
field its selected verifier accepts. Both readings were defensible, and **both reference
implementations independently took the wrong one**: each replayed a genesis
with a forged or missing signature under all three schemes.

Genesis is the record that fixes `mint_authority`, `max_supply` and the
entire initial allocation. Leaving it unauthenticated authenticates every
later event against a root anyone can author — a chain that is sound above
a hinge that is not.

### 5.2 Profile fields

A genesis MAY declare a profile. When it does it carries:

- `profile` — a profile name listed in
  `protocol/satroot1.profile-registry.json`;
- `profile_mode` — the mode that registry pairs with that profile, not a
  free choice;
- the `required_genesis_fields` that registry entry names, each a **non-blank
  string** — non-empty after trimming whitespace, so `"   "` is rejected.

A `profile_mode` **without** a `profile` is rejected. The two are a pair:
either the genesis declares both, or it declares neither and both members
commit JSON `null` (section 7). An unpaired mode was previously validated
against nothing and committed verbatim, so an arbitrary JSON value reached
the state hash and one logical state acquired many spellings.

An unknown profile, a `profile_mode` the registry does not pair with it, or
a missing or empty required field is rejected (section 8.10). Both members
are committed to by section 7; a genesis that declares no profile commits
JSON `null` for each, with the member still present.

This subsection exists because section 7 referred to "the values carried by
the genesis record (section 5)" while section 5 named neither field — a
dangling forward reference an implementer had to resolve by inferring the
names from section 7's own table.

## 6. Event rules

### 6.1 Mint

A `mint` event increases semantic supply.

It is valid only if:

- signer matches mint authority,
- max supply is not exceeded,
- sequence is exactly previous sequence + 1.

### 6.1a Amount encoding

Amounts are written in **canonical form**: no leading zeros. `"400"` is
valid, `"0400"` and `"00"` are not, and `"0"` is the only representation of
zero. Without this a single ledger state has many spellings, and two
byte-distinct ledgers replay identically.

Every amount, balance, and supply value is a base-10 ASCII digit string,
never a JSON number. Amounts carry at most **512 digits**.

The bound exists for determinism, not for capacity: some runtimes limit
integer-from-string conversion (CPython's limit is configurable, with a
floor of 640 digits) while others are unbounded. Without an explicit
protocol bound, the same ledger could replay on one host and fail on
another, which would break the deterministic-replay guarantee. 512 sits
below every such floor, so conforming implementations agree regardless of
host configuration, and the ceiling is far above any realistic supply.

Values that exceed the bound are rejected as invalid, exactly like
non-digit input.

### 6.2 Transfer

A `transfer` event moves semantic balance between accounts.

It is valid only if:

- sender has sufficient balance,
- amount is a positive integer string,
- signer controls the sender account (section 6.7),
- sequence is valid.

### 6.3 Burn

A `burn` event reduces circulating semantic supply.

It is valid only if:

- burner has sufficient balance,
- amount is a positive integer string,
- signer controls the account being burned from (section 6.7).

### 6.4 Rotate authority

A `rotate-authority` event changes the active mint authority for the root namespace.

It is valid only if:

- signer matches the current mint authority,
- `new_mint_authority` is a valid non-empty authority identifier,
- sequence is exactly previous sequence + 1.

This event changes control over future authority-gated actions such as `mint`. It does not move balances by itself and should not be confused with a token transfer.

### 6.5 Freeze / unfreeze account

A `freeze` event changes whether a named account is balance-locked.

It is valid only if:

- signer matches the current mint authority,
- `account` is a valid non-empty account identifier,
- `frozen` is a boolean,
- sequence is exactly previous sequence + 1.

When an account is frozen, balance-affecting lifecycle actions must reject that account as a sender, burner, mint recipient, or transfer recipient until a later `freeze` event sets `frozen=false` for the same account.

This event changes account transferability state. It does not mint, burn, or transfer balances by itself.

### 6.6 Signature verification interface

The reference engine exposes a pluggable signature verifier interface:

```text
verifier(event, signing_payload) -> bool
```

The demo verifier accepts `signature="demo"` for test records. Production deployments should replace it with one of the shipped real schemes (`hmac-sha256`, `ed25519`) or an equivalent verifier over the canonical signing payload.

The reference engine also includes a built-in `hmac-sha256` verifier constructor for controlled environments using shared secrets plus key identifiers. This is a concrete authenticated-event reference path, but it is not a public-key signature scheme.

An `ed25519` path is available when the `cryptography` package is installed; it is the public-key scheme used end to end by the released anchored lanes, without making the base package depend on extra crypto libraries by default.

The reference implementation also exposes helper functions and a small CLI for replaying ledgers plus signing single events or whole event arrays against those reference schemes.

#### 6.6.1 Concrete encodings

**`signature_scheme` is OPTIONAL on every event, genesis or not, and when
absent the event's scheme is `demo`.** The default does not follow the
verifier in use: an event that omits the field is a `demo` event even when
the relying party has configured an `ed25519` or `hmac-sha256` verifier, and
is therefore rejected by that verifier.

This matters because the alternative reading — that an omitted field inherits
whatever verifier happens to be configured — would make the same bytes mean
different things to different relying parties. A record must describe its
own provenance; a verifier must not supply it. An implementation taking the
other reading accepts a signed event that this one rejects, which two
independent implementations did.

A verifier is selected by the event's `signature_scheme`, and the key by its
`signature_key_id`. Each scheme carries its result in the `signature` field
so the scheme is recoverable from the value alone — the two real schemes as
a prefixed lowercase-hex string, `demo` as the literal string `demo`:

| `signature_scheme` | `signature` value |
|---|---|
| `demo` | the literal string `demo` |
| `hmac-sha256` | `"hmac-sha256:" + hex(HMAC-SHA256(key, signing_payload))` |
| `ed25519` | `"ed25519:" + hex(Ed25519-Sign(key, signing_payload))`, 64 bytes |

In both real schemes the message signed is the **`signing_payload` string of
section 2.7, UTF-8 encoded** - it is not hashed first, and no length prefix
or domain separator is added. Ed25519 public keys are raw 32-byte keys as
lowercase hex; RFC 8032 signing is deterministic, so a correct implementation
reproduces the corpus signatures byte for byte.

An event whose `signature_scheme` does not match the verifier in use is
rejected rather than treated as unsigned. For `signature_key_id`:

- under `hmac-sha256` and `ed25519`, a missing, empty, or unknown
  `signature_key_id` is rejected;
- under `demo`, `signature_key_id` MUST be absent, and an event carrying one
  is rejected.

Stated as two cases because the single unqualified sentence this replaces
contradicted the `demo` rule.

**The scheme-match check is load-bearing, and easy to omit.** The tempting
argument for skipping it is that a verifier ignoring `signature_scheme`
would still fail on a signature made under another scheme, because the bytes
differ and each scheme prefixes its own name. That covers only the case
where the signature and the declared scheme agree with each other but not
with the verifier.

It misses the opposite case: **a signature that is valid for the verifier in
use, while the declared scheme lies.** A `demo` record carrying
`signature: "demo"` but `signature_scheme: "ed25519"` presents bytes the
demo verifier would otherwise accept; only the scheme check rejects it.
Without it a record can misrepresent its own provenance and still validate.

`reject-genesis-scheme-mismatch` pins this. An implementation that never
reads `signature_scheme` — and therefore cannot apply the scheme-dependent
`signature_key_id` rules either — accepts that record, and the corpus
catches it there.

Two earlier revisions of this paragraph were wrong, in opposite directions.
The first asserted the rule could not be isolated by any vector, which told
implementers it was unobservable and therefore skippable. The second claimed
the vector already pinned it, which was measured against an incoherent
ablation: one that dropped the check from the verifier while still applying
scheme-dependent metadata rules. The vector genuinely did not pin the rule
until it stopped carrying a `signature_key_id`, because that field made a
scheme-blind implementation reject it for a reason the corpus already tests
elsewhere.

**The HMAC key is the secret's UTF-8 bytes, not a decoding of them.** Where
a shared secret is written as a 64-character hex string, the MAC key is
those 64 ASCII characters, *not* the 32 bytes they encode. This is the one
place in this specification where the obvious reading is the wrong one, so
it is stated rather than implied: a conforming implementation that
hex-decodes the secret produces a different MAC for every event and cannot
be made to agree by any other means.

CLI replay may be configured against the same reference verification models, so signed ledgers can be validated end to end without dropping into the Python API.

The reference implementation also exposes schema validation helpers and a CLI validation path so raw event JSON can be checked against `protocol/satroot1.schema.json` before replay.

It also exposes ledger-annotation helpers so deterministic `event_id` and `state_hash` commitments can be attached to an already valid ledger without changing the signed payload model.

For Ed25519 workflows, the reference implementation also exposes public-key derivation helpers so replay-ready verifier key maps can be produced from private-key maps without custom glue code.

It also exposes private-key generation helpers for reference and test workflows, allowing SATROOT-specific key maps to be bootstrapped directly from the CLI before deriving public verifier material.

For multi-signer ledgers, the reference implementation also exposes signer-map bootstrapping helpers so `signer -> key_id` mappings can be derived from event history before generating or assigning concrete verifier material.

For convenience workflows, those pieces can also be composed into a one-shot Ed25519 bootstrap path that emits signer maps plus private/public key material for a ledger without additional glue code.

The same pattern is exposed for controlled shared-secret deployments, where signer maps and HMAC verifier material can be bootstrapped directly from a ledger for reference and test workflows.

The reference CLI may also expose profile-aware genesis scaffolding so valid base or profiled `genesis` objects can be emitted with safe defaults before downstream replay, signing, or bundling steps.

The reference CLI may also expose event scaffolding helpers so valid non-genesis `mint`, `transfer`, `burn`, `freeze`, or `rotate-authority` records can be derived from an existing ledger tip or from explicit `root_id`, `sequence`, and `prev_event_id` inputs.

Those helpers may also be composed into append workflows so an existing ledger can be replayed, a next event scaffolded or supplied, and that new event signed and appended in one step without manual JSON surgery.

For profile-specific ergonomics, the reference CLI may also expose lifecycle helpers that map draft profile semantics to ordinary SATROOT events. For example, a `SATROOT-MACHINE-1` ledger with `consumption_model=burn-on-use` may support a helper that appends the corresponding `burn` event without forcing the operator to restate the generic lifecycle mapping each time.

Likewise, singleton receipt, identity, or license profiles may support transfer helpers that detect the current active holder and append the corresponding one-unit reassignment without restating the generic SATROOT event details each time. Those same profiles may also support archival helpers that move the active unit into an archive account and retirement helpers that burn an already archived singleton object once the archived holder is ready to retire it.

The reference CLI may also expose singleton demo bootstrap paths that scaffold runnable receipt, identity, or license lifecycle ledgers from profile-aware defaults so object-style SATROOT workflows can be generated without hand-authoring each lifecycle record.

Those singleton demo paths may also be composed directly into signed bundle workflows so object-style profiles can emit verifier material, annotated replay artifacts, and bundle manifests without a separately prepared intermediate ledger file.

Those singleton bundle workflows may also be composed one step further into release bootstraps so receipt, identity, or license profile artifacts can emit both signed bundles and signed release directories through the same bundle-index and release-manifest verification path used elsewhere in SATROOT.

For reference-only stable ledgers, the reference CLI may also expose a demo bootstrap path that scaffolds a runnable `SATROOT-STABLE-1` issuance, distribution, and optional burn flow into reusable JSON artifacts without introducing redemption or reserve semantics.

That same stable bootstrap may also be composed directly into a signed bundle path so a reference-only stable ledger can be emitted together with signer material, annotated replay artifacts, and a verifiable bundle manifest without requiring a separate handwritten intermediate ledger file.

That signed stable bundle path may also be composed one step further into a release bootstrap that writes both the stable bundle and a signed release directory together, preserving the reference-only stable semantics while exposing the same bundle-index and release-manifest verification flow used elsewhere in SATROOT.

That scaffolding may also be composed into a one-shot starter-bundle workflow that emits a scaffolded `genesis.json`, a one-record signed ledger bundle, and verifier material in a single directory for reference or testing.

Those workflow pieces can also be composed into a one-shot signed-ledger bundle path, allowing a ledger plus verifier material and signed/annotated artifacts to be emitted together for reference or testing.

Signed bundle workflows may also emit a machine-readable manifest describing the chosen scheme, generated files, verifier-material scope, per-file hashes, record count, full final replay snapshot, and final committed SATROOT state hash so downstream tooling can inspect bundles without replaying them first.

For release distribution workflows, the reference CLI may also expose a publication bootstrap helper that generates release signing material and writes `bundle_index.json` plus `release_manifest.json` into a ready-to-verify release directory in one step.

For `ed25519` workflows, the reference CLI may emit either a `private-and-public` bundle for local workflow portability or a `public-only` verifier bundle that omits private keys while preserving end-to-end replay verification.

The reference implementation also exposes bundle-verification helpers so a signed bundle directory can be checked against its manifest and verifier material before any consumer accepts it.

The signed bundle manifest format is also described by its own JSON Schema so bundle producers and consumers can validate the exported metadata contract independently of replay.

When replay is unnecessary, the reference CLI may also expose manifest-only inspection helpers that summarize bundle metadata and the embedded final replay snapshot directly from `bundle_manifest.json`.

The reference CLI may also expose non-replay lint helpers that check declared bundle files, hash coverage, and directory-layout drift before a consumer decides whether full cryptographic replay verification is worth running.

For multi-bundle releases, the reference implementation may also emit deterministic bundle-index catalogs that point at one or more `bundle_manifest.json` artifacts, record each manifest hash, and summarize the final committed state for downstream release tooling.

Those bundle indexes may also carry optional release metadata such as channel, human label, and published-at timestamp so the same artifact can serve as a lightweight SATROOT distribution manifest.

For authenticated publication workflows, the reference implementation may also emit a signed release manifest that binds a `bundle_index.json` path and hash to explicit release-signature metadata, allowing downstream consumers to verify the publication artifact separately from bundle replay itself.

The reference CLI may also expose release-key bootstrap helpers so publication signing material can be generated and reused as files rather than injected only through one-off inline secret or private-key parameters.

The reference CLI may also expose a one-shot publication helper that writes `bundle_index.json` and `release_manifest.json` together into a release directory while preserving relative bundle paths for downstream verification.

The reference engine currently recognizes these signature metadata rules:

- `demo`: `signature` must be `demo` and `signature_key_id` must be absent.
- `hmac-sha256`: `signature_key_id` is required and the signature must use the `hmac-sha256:` prefix.
- `ed25519`: `signature_key_id` is required and the signature must use the `ed25519:` prefix.

### 6.7 Account control

**A signer controls an account when `signer` equals the account name
exactly** — byte-for-byte string equality, with no normalisation.

That is the whole rule at this layer. Section 9 says binding a cryptographic
key to an account is an application-level concern, and it remains so: this
specification checks only that a record's `signer` names the account whose
balance moves, and that the record's signature verifies under the configured
verifier for the key it names.

It is stated because "signer controls sender account" was previously left
undefined. Two independent implementations both had to guess it; both
guessed equality and the corpus agreed with them, but the document did not
say so.

## 7. State commitment

Each event SHOULD include a `state_hash` after application:

```text
state_hash = "sha256:" + hex(sha256(canonical_json(commitment_snapshot)))
```

where `commitment_snapshot` is exactly these thirteen members:

| member | form |
|---|---|
| `root_id` | string |
| `symbol` | string |
| `name` | string |
| `decimals` | number |
| `max_supply` | digit string, or `null` if unbounded |
| `mint_authority` | string |
| `profile` | the genesis profile, or `null` |
| `profile_mode` | the genesis profile mode, or `null` |
| `balances` | object of account to digit string, **accounts with a zero balance omitted** |
| `frozen_accounts` | array of account strings, sorted |
| `supply` | digit string |
| `sequence` | number |
| `last_event_id` | the `event_id` of the most recently applied event |

Key order in the serialised form is imposed by canonical JSON (section 2.6),
so the table order above is descriptive rather than normative.

Three of these members need defining because they are committed to but not
established elsewhere:

- **`supply` is circulating supply** — the sum of all balances — not
  cumulative minted. Mint increases it, burn decreases it, and `max_supply`
  bounds *it*, so a burn followed by a mint is permitted even where the
  cumulative total minted would exceed `max_supply`.
- **`profile` and `profile_mode`** are the values carried by the genesis
  record (section 5). They are optional there, and when absent the committed
  value is JSON `null` — **the member is still present in the snapshot**.
  Omitting the key instead would change every state hash, so the distinction
  is normative.
- **`last_event_id`** is the `event_id` of the most recently applied event,
  computed per section 2.7 whether or not the event carried one. For a
  ledger of one genesis record it is that record's id, not `null`.

This lets lightweight clients check that independent indexers agree on the
same state.

An implementation may keep richer replay state for its own tooling -
transfer models, preserved genesis metadata - but anything outside the
thirteen members above is not committed to and must not affect the hash.

An event MAY also carry an `event_id`. If present, it MUST equal the canonical event hash calculated from the record content excluding the `event_id` and `state_hash` fields. This avoids a circular dependency between event identity and post-application state commitment.

The reference implementation may expose richer replay snapshots for developer tooling, including preserved genesis/profile metadata, but the state commitment hash should remain derived from a stable deterministic subset of protocol state.

## 8. Minimal validity conditions

A SATROOT-1 indexer MUST reject a ledger if:

1. more than one genesis exists for the same root_id,
2. sequence numbers skip or repeat,
3. a transfer spends unavailable balance,
4. a mint exceeds max supply,
5. an event uses a different root_id,
6. an authority rotation is attempted by a non-authority signer,
7. a required signature check fails, on any event including the genesis
   record (section 5.1),
8. canonical JSON hashing does not match the stated event ID,
9. a stated `state_hash` does not match replayed state,
10. an unknown profile or invalid profile mode is used.

## 9. Claim discipline

SATROOT-1 can truthfully say:

- one satoshi anchors the token ledger,
- token units are protocol-defined semantic units,
- token supply can be arbitrarily large if the protocol permits it,
- balances are computed by replaying protocol events,
- one real one-satoshi testnet outpoint has been bound as a namespace `root_id` with an ed25519-verified lifecycle,
- a section 4 state commitment for that namespace has been broadcast on-chain and re-verified offline from raw transaction bytes.

SATROOT-1 should not say:

- Bitcoin itself has been subdivided below one satoshi,
- semantic units are native Bitcoin units,
- the token has legal/economic rights unless separately documented,
- wallets or exchanges will recognize it without integration,
- the frozen kernel binds a signing key to the account it signs for — it checks the `signer` string and a valid signature under some registered key, but key-to-account binding is an application-level responsibility (see `KEY_MANAGEMENT.md`).

## 10. Stable-value boundary

Stable-value, fiat-reference, or stablecoin-like designs MUST be implemented as separate profiles. The SATROOT-1 base primitive does not create a stablecoin, redemption right, reserve claim, bank deposit, e-money token, or investment instrument.

The released `SATROOT-STABLE-1` profile defines reference-only accounting units such as `USDROOT1`, but the base protocol remains only a one-satoshi-root semantic ledger primitive.

## 11. Namespace expansion boundary

Further SATROOT work may define additional object classes beyond the six registered profiles under the same root model, but those profiles must not retroactively change the minimal meaning of `SATROOT-1`.

`SATROOT-1` remains:

- one root satoshi,
- one semantic token ledger,
- deterministic replay,
- strict boundaries around claims.

## 12. First demo token

Demo name: One Satoshi Floor Token
Symbol: FLOOR1
Root supply: 1,000,000,000 units
Root satoshi: one UTXO
Decimals: 0
Meaning: proof-of-concept semantic units anchored to one satoshi
