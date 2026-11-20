"""Data masking.

Techniques used
- Pseudonymisation of identifiers with a keyed hash (HMAC-SHA256). Deterministic, so the same customer
  always gets the same token and joins/aggregations still work, but the original ID cannot be recovered
  or guessed by dictionary attack without the secret key.
- Generalisation of postal codes to a short prefix (e.g. 90036 -> 900**), reducing re-identification risk
  while keeping regional analysis possible.

Masking happens at the edge of the pipeline: the warehouse, marts, workbooks and decks only ever see
masked data.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import warnings

import pandas as pd

DEV_KEY = b"dev-only-masking-key-do-not-use-in-production"
TOKEN_PREFIX = "C-"
TOKEN_HEX_LENGTH = 12            # 48 bits: collision-free for this population (asserted below)


class MaskingKeyError(RuntimeError):
    pass


def get_key(env_var: str = "MASKING_KEY", strict: bool = False) -> bytes:
    """Read the secret key from the environment. Without one, fall back to a dev key with a warning."""
    value = os.environ.get(env_var)
    if value:
        return value.encode("utf-8")
    if strict:
        raise MaskingKeyError(f"environment variable {env_var} is required in strict mode")
    warnings.warn(f"{env_var} is not set: using the public DEV key. Tokens are NOT secure.", stacklevel=2)
    return DEV_KEY


def pseudonymize(values: pd.Series, key: bytes) -> pd.Series:
    """Map each distinct value to a stable token such as `C-3f9a1c0b7d2e`."""
    uniques = values.astype(str).unique()
    mapping = {
        v: TOKEN_PREFIX + hmac.new(key, v.encode("utf-8"), hashlib.sha256).hexdigest()[:TOKEN_HEX_LENGTH]
        for v in uniques
    }
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("token collision detected; increase TOKEN_HEX_LENGTH")
    return values.astype(str).map(mapping)


def generalize_postal(codes: pd.Series, keep: int = 3) -> pd.Series:
    """Left-pad to 5 digits (leading zeros are often lost in CSV/Excel) and keep the first `keep` digits."""
    padded = codes.astype("string").str.strip().str.zfill(5)
    return padded.str.slice(0, keep) + "*" * (5 - keep)


def k_anonymity(df: pd.DataFrame, quasi_identifiers: list[str]) -> int:
    """Size of the smallest group of rows that share the same quasi-identifier values."""
    return int(df.groupby(quasi_identifiers, observed=True).size().min())


def mask_orders(df: pd.DataFrame, key: bytes, postal_prefix_len: int = 3) -> tuple[pd.DataFrame, dict]:
    """Return a masked copy of the orders frame plus a report describing what was done."""
    original_ids = df["Customer ID"].astype(str).unique()
    out = df.copy()
    out["Customer ID"] = pseudonymize(df["Customer ID"], key)
    out["Postal Prefix"] = generalize_postal(df["Postal Code"], postal_prefix_len)
    out = out.drop(columns=["Postal Code"])

    leaked = assert_no_leak(out, original_ids)
    report = {
        "technique_customer_id": "HMAC-SHA256 pseudonymisation",
        "technique_postal_code": f"generalised to {postal_prefix_len}-digit prefix",
        "distinct_customers_masked": int(len(original_ids)),
        "raw_customer_ids_found_in_output": leaked,
        "k_anonymity_postal_prefix_segment": k_anonymity(out, ["Postal Prefix", "Segment"]),
    }
    return out, report


def assert_no_leak(masked: pd.DataFrame, original_ids) -> int:
    """Count original customer IDs that still appear anywhere in the masked data (must be 0)."""
    originals = set(map(str, original_ids))
    leaked = 0
    for col in masked.select_dtypes(include=["object", "string"]).columns:
        leaked += int(masked[col].astype(str).isin(originals).sum())
    if leaked:
        raise RuntimeError(f"masking failed: {leaked} raw customer IDs remain in the output")
    return leaked
