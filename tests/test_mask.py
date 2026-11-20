import warnings

import pandas as pd
import pytest

from superstore_pipeline import mask

KEY = b"unit-test-key"


def test_pseudonymize_is_deterministic_and_keyed():
    s = pd.Series(["AB-123", "CD-456", "AB-123"])
    a, b = mask.pseudonymize(s, KEY), mask.pseudonymize(s, KEY)
    assert a.equals(b)
    assert a.iloc[0] == a.iloc[2] != a.iloc[1]          # same input -> same token, different input -> different
    assert not mask.pseudonymize(s, b"another-key").equals(a)


def test_tokens_have_expected_shape_and_hide_the_original():
    token = mask.pseudonymize(pd.Series(["AB-123"]), KEY).iloc[0]
    assert token.startswith("C-") and len(token) == 2 + mask.TOKEN_HEX_LENGTH
    assert "AB-123" not in token


@pytest.mark.parametrize("raw,expected", [("90036", "900**"), ("2142", "021**"), ("10009", "100**"), ("501", "005**")])
def test_postal_generalisation_restores_leading_zeros(raw, expected):
    assert mask.generalize_postal(pd.Series([raw], dtype="string"), 3).iloc[0] == expected


def test_mask_orders_removes_raw_identifiers(raw_df):
    masked, report = mask.mask_orders(raw_df, KEY)
    assert "Postal Code" not in masked.columns and "Postal Prefix" in masked.columns
    assert report["raw_customer_ids_found_in_output"] == 0
    assert not set(raw_df["Customer ID"]) & set(masked["Customer ID"])
    assert masked["Customer ID"].nunique() == raw_df["Customer ID"].nunique()     # no collisions, no merges


def test_masking_does_not_change_business_values(raw_df):
    masked, _ = mask.mask_orders(raw_df, KEY)
    for col in ("Sales", "Profit", "Quantity", "Discount"):
        assert masked[col].sum() == pytest.approx(raw_df[col].sum())
    assert len(masked) == len(raw_df)


def test_assert_no_leak_detects_a_leak(raw_df):
    leaky = raw_df.copy()
    with pytest.raises(RuntimeError, match="masking failed"):
        mask.assert_no_leak(leaky, raw_df["Customer ID"].unique())


def test_strict_mode_requires_a_key(monkeypatch):
    monkeypatch.delenv("MASKING_KEY", raising=False)
    with pytest.raises(mask.MaskingKeyError):
        mask.get_key("MASKING_KEY", strict=True)
    with pytest.warns(UserWarning, match="DEV key"):
        assert mask.get_key("MASKING_KEY") == mask.DEV_KEY


def test_environment_key_is_used(monkeypatch):
    monkeypatch.setenv("MASKING_KEY", "s3cret")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert mask.get_key("MASKING_KEY", strict=True) == b"s3cret"


def test_k_anonymity_counts_smallest_group():
    df = pd.DataFrame({"a": ["x", "x", "y"], "b": [1, 1, 1]})
    assert mask.k_anonymity(df, ["a", "b"]) == 1
