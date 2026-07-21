# Evidence export and chain-of-custody manual

## Custody semantics

CHH records the requester, membership, school, conversation, active review, purpose, timestamps, counts, artifact hash, canonical manifest hash, verification result, expiry, bounded downloads, and each download. Generation is a leased PostgreSQL job. The worker revalidates the active user, membership, export permission, optional note-export permission, and review scope before reading content.

The ZIP contains `manifest.json`, `transcript.html`, and declared media. Every declared file has SHA-256 and size. The manifest's `integrity.canonical_payload_sha256` hashes sorted compact UTF-8 JSON with the integrity object omitted. CHH verifies safe unique relative names, rejects encryption/symlinks/path traversal, bounds entry count/uncompressed size, checks all declared sizes/hashes, rejects undeclared files, and checks the final artifact hash before marking it ready.

## Operator procedure

1. Record the formal authority/case reference outside CHH as required by school policy.
2. Start an authorised review and request the export with a meaningful purpose.
3. Wait for `ready` and `verified`; do not treat `requested` or `generating` as evidence.
4. Download once to an approved encrypted case location.
5. Record both hashes and the CHH export ID in the case log.
6. Run `python backend/scripts/verify_evidence_export.py PACKAGE --artifact-sha256 HASH --manifest-sha256 HASH` before transfer or use.
7. Transfer only through the approved evidence channel. Never use a public link or email attachment.
8. Retain export metadata under policy even after the short-lived artifact expires.

Verification proves byte integrity relative to the recorded hashes. It does not prove the truth of a message, legal admissibility, or compliance; those require authorised local review.
