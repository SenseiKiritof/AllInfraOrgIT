# ADR-009 — Credential encryption with SSecureUtils

- Status: accepted
- Date: 2026-10-28

## Context

`ServerCredentials` stores SSH secrets encrypted at rest, with a key per version in `ServerAccess:CredentialKeys:<n>` and the version on the row. The AES-GCM code was local: `CredentialCipher` in the API and `LegacyCipher` in the importer. The same primitive is available as the open-source package `SSecureUtils` 1.1.1 (MIT, .NET 6/7/8 assets, compatible with this net10.0 solution), which also offers `AddSecureConfig` to decrypt whole `appsettings.*.Secure.json` files.

The library is not a drop-in replacement: it derives the AES key with SHA-256 from the configured string and prefixes the output with `v2:`, while the previous format used the base64-decoded key directly and had no prefix.

## Decision

- `SSecureUtils` 1.1.1 is a dependency of the API, `tools/LegacyImport` and `tools/RewrapCredentials`.
- `CredentialCipher` keeps the versioning and the configuration contract (`ServerAccess:CredentialKeys:<n>`, 32-byte base64, `CurrentKeyVersion`) and delegates only the crypto to `SecureUtils.Encrypt/Decrypt`.
- Stored format: `v2:` + `base64(nonce 12 | tag 16 | ciphertext)`; the AES key is `SHA256(UTF8(configured string))`.
- `LegacyCipher` stays on the legacy format (raw key, no prefix) because it reads the old database; the importer writes the new format with `SecureUtils` directly.
- Encrypted configuration: the API loads `appsettings.<Environment>.Secure.json` when the file exists, decrypting every value with `ENC_KEY`. If the file exists and `ENC_KEY` is missing, startup fails instead of silently ignoring the secrets.
- Existing rows are converted once by `tools/RewrapCredentials` (dry-run by default, `--apply` to write, idempotent on the `v2:` prefix).

## Alternatives considered

- **Keep the local AES-GCM code**: rejected, it duplicates a library that is already maintained and used elsewhere.
- **Accept both formats in the API**: rejected, it keeps two crypto paths at runtime forever; the one-shot rewrap covers the transition.
- **Adopt only `AddSecureConfig`**: rejected, it covers configuration files, not the credentials in MySQL.

## Consequences

- One crypto implementation, authenticated AES-GCM in both paths, and encrypted configuration available.
- A database written before this change needs the rewrap before the new API can read its credentials; rows left unwrapped make SSH fail with a decryption error.
- Key rotation is unchanged: the row keeps `KeyVersion` and each version keeps its key.
- The library targets .NET 8 at most; the net8.0 asset is used on .NET 10 and must be revisited if the package stalls.
