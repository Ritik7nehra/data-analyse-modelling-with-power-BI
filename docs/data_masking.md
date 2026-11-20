# Data masking

What is masked, how, and what that does and does not protect.

## What the pipeline does

| Field | Technique | Result |
|---|---|---|
| Customer ID (e.g. `CG-12520`) | Pseudonymisation with a keyed hash: HMAC-SHA256, first 12 hex characters | Stable token such as `C-66e1c3a92526`. The same customer always gets the same token, so joins, counts and RFM still work |
| Postal code (e.g. `77095`) | Generalisation to a 3-digit prefix | `770**`. Regional analysis still works; the exact area is not exposed |
| Customer name | Not carried into the pipeline | `data/superstore_orders.csv` omits names |

Masking runs right after validation and before anything is loaded, so the warehouse, marts, Excel workbooks and the deck only ever see tokens. `assert_no_leak` fails the run if any raw customer ID appears anywhere in the masked data.

## Key management

The HMAC key is read from the `MASKING_KEY` environment variable (name set in `config/pipeline.yml`).

- **Production:** keep the key in a secret manager (GitHub Actions secret, Google Secret Manager, Azure Key Vault) and run with `--strict-masking`, which refuses to start without it.
- **Local development:** without a key the pipeline falls back to a **public dev key** and warns. This is deliberate so the repo runs out of the box.
- **Rotation:** changing the key changes every token. Do it on a schedule that your downstream joins can tolerate (tokens are not stable across keys).

> **The committed outputs use the public dev key.** `reports/marts/*.csv`, the Excel workbooks and the deck were built that way, so their tokens provide no secrecy: anyone can recompute them. That is acceptable here only because the source is a public, fictional sample data set whose raw IDs are already in `data/`. In a real deployment, never commit tokens made with a shared key, and never commit the key.

## What is verified

- `tests/test_mask.py`: tokens are deterministic and depend on the key; they have the expected shape and hide the original; postcodes regain leading zeros; masking leaves business values unchanged; the leak detector catches a leak; strict mode refuses to run without a key; an environment key is used when set; the k-anonymity helper counts the smallest group.
- `tests/test_pipeline.py` and `tests/test_marts.py`: the warehouse and every mart contain no raw customer IDs.
- The CI workflow is written to run the pipeline in strict mode with an ephemeral key (not yet run on GitHub; the same command was run locally).

## Limits (read before relying on this)

- **Pseudonymisation is not anonymisation.** Whoever holds the key can regenerate tokens for candidate IDs. Customer IDs here are short (two letters and digits), so the key is the only thing preventing a dictionary attack. Treat the key as the secret.
- **Quasi-identifiers remain.** The run reports k-anonymity over (postal prefix, segment) and it is **1**: at least one combination identifies a single row. Generalising postcodes alone does not make the data anonymous; combine with further generalisation or suppression if the data were sensitive.
- **Order dates and product names are unmasked.** They are not personal data here, but in other data sets they could be.
- **No format-preserving tokens.** Tokens do not look like the original IDs, which is a feature for privacy and a cost for legacy systems that validate formats.

## Equivalents in the other tools

| Tool | Comparable control |
|---|---|
| BigQuery | Column-level security with policy tags; dynamic data masking rules on columns |
| Microsoft Fabric / SQL | Dynamic data masking in the Warehouse SQL endpoint; sensitivity labels |
| Power BI | Row-level and object-level security in the semantic model |

These are pointers to features, not configurations included in this repo. Check each vendor's current documentation.
