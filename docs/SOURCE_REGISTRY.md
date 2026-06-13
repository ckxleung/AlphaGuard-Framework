# AlphaGuard Source Registry Standard

## Purpose

Financial claims must resolve to an identifiable document snapshot, not merely
to a website homepage. AlphaGuard therefore separates source control into two
linked records:

1. `config/source_registry.json` registers the identity and integrity of each
   source document;
2. each publication artifact records the precise page, section, table, exhibit,
   paragraph, cell range, timestamp, line range, or JSON pointer used.

This design prevents a citation from silently drifting when a document is
replaced, amended, moved, or quoted without a reproducible location.

## Registered Document Contract

Every registered document requires:

| Field | Requirement |
|---|---|
| `document_id` | Stable and unique repository-wide identifier |
| `publisher` | Issuer, regulator, exchange, data provider, or research entity |
| `title` | Exact document title |
| `document_type` | Approved source category |
| `jurisdiction` | Applicable market or regulatory jurisdiction |
| `publication_date` | ISO-8601 document date |
| `canonical_url` | Direct HTTP(S) document location |
| `retrieved_at` | ISO-8601 retrieval timestamp with timezone |
| `content_hash` | SHA-256 hash of the retrieved snapshot |
| `language` | Source-document language |
| `primary_source` | Whether the record is first-party or authoritative |
| `local_path` | Optional repository-relative retained snapshot |

Approved document types are:

- `REGULATORY_FILING`;
- `EXCHANGE_DISCLOSURE`;
- `COMPANY_IR`;
- `OFFICIAL_DATASET`;
- `MARKET_DATA`;
- `RESEARCH`;
- `SOCIAL_MEDIA`;
- `INTERNAL_FIXTURE`.

## Document ID Convention

Use durable IDs that do not depend on list order:

```text
DOC-{PUBLISHER}-{DOCUMENT_TYPE}-{DATE}-{SEQUENCE}
```

Examples:

```text
DOC-SEC-10K-20260225-NVDA
DOC-HKEX-ANNOUNCEMENT-20260613-00100
DOC-MINIMAX-IR-20260613-RESULTS
```

Do not reuse an ID for an amended or replaced document. Register a new snapshot
and retain the prior record when historical reproducibility matters.

## Citation Locator Contract

Every source entry in a publication artifact must include:

```json
{
  "source_id": "SRC-001",
  "registry_document_id": "DOC-SEC-10K-20260225-NVDA",
  "title": "Exact registered title",
  "url": "https://direct-document-url",
  "accessed_at": "2026-06-13T10:00:00+08:00",
  "content_hash": "sha256:...",
  "locator": {
    "type": "PAGE",
    "value": "p. 87, Note 7, Debt"
  }
}
```

Supported locator types:

- `PAGE`;
- `SECTION`;
- `TABLE`;
- `EXHIBIT`;
- `PARAGRAPH`;
- `CELL_RANGE`;
- `TIMESTAMP`;
- `LINE_RANGE`;
- `JSON_POINTER`.

The locator must be specific enough for another reviewer to find the evidence
without searching the entire document.

## Primary-Source Priority

Use this order unless a kernel explicitly requires another evidence class:

1. regulatory filings and exchange disclosures;
2. company investor-relations documents;
3. official datasets and regulator publications;
4. timestamped licensed or public market data;
5. reputable secondary research;
6. social-media evidence for behavioral analysis only.

Secondary research may explain context but should not replace an available
primary source for reported financial figures, capital structure, legal terms,
or regulatory requirements.

## Integrity Workflow

1. retrieve the exact source document;
2. retain a snapshot where licensing permits;
3. calculate SHA-256 over the retrieved bytes;
4. register metadata in `config/source_registry.json`;
5. validate the registry;
6. cite the registered ID and exact locator in the artifact;
7. validate the artifact before publication.

Commands:

```bash
python3 src/source_registry.py config/source_registry.json
python3 src/output_standard.py examples/publication_artifact.example.json
python3 -m src.repository_validator
```

## Security and Licensing Boundary

The public registry must not contain credentials, signed URLs, licensed data
payloads, confidential research, or non-public deal documents. For restricted
sources, register only metadata that may legally be disclosed and keep the
snapshot in an approved private evidence store. The hash can prove snapshot
identity without publishing the underlying content.

