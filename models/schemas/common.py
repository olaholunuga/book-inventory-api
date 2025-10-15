from datetime import date
from decimal import Decimal, InvalidOperation

from marshmallow import ValidationError


def normalize_isbn(raw: str) -> str:
    if raw is None:
        raise ValidationError("ISBN is required.")
    digits = "".join(ch for ch in raw if ch.isdigit() or ch.upper() == "X")
    # Keep 'X' only for ISBN-10 check-digit position
    return digits


def _is_valid_isbn10(digits: str) -> bool:
    if len(digits) != 10:
        return False
    # 'X' allowed only at last position
    total = 0
    for i, ch in enumerate(digits[:9], start=1):
        if not ch.isdigit():
            return False
        total += int(ch) * i
    check = digits[9]
    if check == "X":
        total += 10 * 10
    elif check.isdigit():
        total += int(check) * 10
    else:
        return False
    return total % 11 == 0


def _is_valid_isbn13(digits: str) -> bool:
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(digits[:12]):
        factor = 1 if i % 2 == 0 else 3
        total += int(ch) * factor
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(digits[12])


def validate_and_normalize_isbn(raw: str) -> str:
    digits = normalize_isbn(raw).upper()
    if len(digits) == 10 and _is_valid_isbn10(digits):
        # Store ISBN-10 as digits-only (with possible X at end)
        return digits
    if len(digits) == 13 and _is_valid_isbn13(digits):
        return digits
    raise ValidationError("Invalid ISBN-10 or ISBN-13.")


def validate_not_future(d: date) -> None:
    if d and d > date.today():
        raise ValidationError("Date cannot be in the future.")


def to_decimal_2(value) -> Decimal:
    if value is None:
        return None
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValidationError("Invalid decimal.")
    if d < 0:
        raise ValidationError("Must be greater than or equal to 0.")
    # Quantize to 2 decimal places when dumping if needed in API layer
    return d