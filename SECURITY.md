# Security reporting and boundaries

## Supported use

V1 is a loopback-only local demonstration with synthetic data. Its freely selectable receiver/reviewer identities are not production authentication. The repository provides no production deployment or live vendor connector.

The application validates data and roles, checks versions, constrains uploads, and records decisions. These are useful draft controls, not a complete security assessment or a guarantee that the service is safe for real warehouse records.

## Report a concern

Contact the project owner privately through the existing project workspace. A dedicated security address has not been established. Do not put a vulnerability, credential, database, operational receipt, or private image in a public issue. Include a minimal synthetic reproduction, affected version, expected behavior, observed behavior, and impact.

The maintainer should acknowledge the report, preserve relevant evidence, reproduce it in a private test environment, decide remediation and disclosure together, and document the fixed version. No response-time promise has been agreed for this draft.

## Sensitive locations

- The configured `HH_DATA_DIR`, including the database, images, and any backups.
- Environment files and model-service configuration.
- Exported receipts and audit records.
- Actual partner catalogs, forms, documents, and vendor API details.

Keep these outside public version control. An `.env.example` must contain placeholders and safe defaults only. If a secret was accidentally committed, removing the file is not enough: revoke or rotate the secret and assess the history privately.

## Before wider use

Implement real identity and access control, transport security, a secret-management process, validated vendor permissions, approved logs and retention, dependency maintenance, monitoring, backup recovery, and incident ownership. Review model inputs and outputs as untrusted data. Do not use a model response to authorize stock changes.
