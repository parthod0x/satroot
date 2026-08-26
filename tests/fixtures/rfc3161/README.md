# Real RFC 3161 timestamp tokens

Two genuine `TimeStampResp` structures, obtained 2026-08-26 by submitting a
`TimeStampReq` built by `satroot_commitment.build_timestamp_request` to two
independent public Time-Stamp Authorities.

Both commit to the same digest: the SHA-256 of the SATROOT commitment document
binding `root_id = ab..ab:0` to `state_hash = sha256:11..11`.

| file | authority | signingCertificate form |
|---|---|---|
| `freetsa-org.tsr` | freetsa.org (DE) | `signingCertificate` (ESS v1) |
| `digicert.tsr` | DigiCert | `signingCertificateV2` (RFC 5035) |

**Why these are checked in.** Until 2026-08-26 no test had ever handed the
parser a real token. Every fixture was a `TimeStampReq` the module had built
itself and fed back to its own parser, so implementation and tests shared one
wrong model of the ASN.1: `extract_message_imprint` descended only into
SEQUENCEs and could not cross the `[0] EXPLICIT`, `SET` and `OCTET STRING`
hops that stand between `ContentInfo` and `TSTInfo`. It rejected every real
token and accepted any DER carrying a matching shape. Two external reviewers
found it independently; these files are what stops it coming back.

Neither file contains a secret. A timestamp token is public evidence: a TSA
signature over a digest, a time, and the TSA's own certificate chain.

To regenerate:

```
python -c "import satroot_commitment as sc; \
  d=sc.commitment_digest(sc.build_commitment_bytes('ab'*32+':0','sha256:'+'11'*32)); \
  open('req.tsq','wb').write(sc.build_timestamp_request(d))"
curl -H "Content-Type: application/timestamp-query" --data-binary @req.tsq \
     https://freetsa.org/tsr -o freetsa-org.tsr
```
