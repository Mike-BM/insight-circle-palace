import pytest
from app.services.mpesa import normalize_phone_number, MEMBERSHIP_FEE_KES


def test_phone_normalization_valid():
    assert normalize_phone_number("0712345678") == "254712345678"
    assert normalize_phone_number("0722000000") == "254722000000"
    assert normalize_phone_number("0110000000") == "254110000000"
    assert normalize_phone_number("+254712345678") == "254712345678"
    assert normalize_phone_number("+254 712 345 678") == "254712345678"
    assert normalize_phone_number("254712345678") == "254712345678"
    assert normalize_phone_number("712345678") == "254712345678"
    assert normalize_phone_number("112345678") == "254112345678"


def test_phone_normalization_invalid():
    with pytest.raises(ValueError):
        normalize_phone_number("")

    with pytest.raises(ValueError):
        normalize_phone_number("12345")

    with pytest.raises(ValueError):
        normalize_phone_number("0201234567")  # Landline

    with pytest.raises(ValueError):
        normalize_phone_number("+15551234567")  # US number


def test_membership_fee_constant():
    assert MEMBERSHIP_FEE_KES == 250.0
