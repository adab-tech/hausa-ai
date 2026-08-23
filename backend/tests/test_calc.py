"""Tests for the safe arithmetic evaluator.

The security tests are the important ones: calculate() must NEVER execute
arbitrary code — hostile input returns None, not a side effect.
"""

from services.calc_service import calculate, looks_like_math


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------
def test_basic_arithmetic():
    assert calculate("2+2") == "4"
    assert calculate("45*12") == "540"
    assert calculate("(3+4)*2") == "14"
    assert calculate("2**10") == "1024"
    assert calculate("10/4") == "2.5"
    assert calculate("17 % 5") == "2"


def test_operator_precedence():
    assert calculate("2 + 3 * 4") == "14"
    assert calculate("(2 + 3) * 4") == "20"


def test_functions_and_constants():
    assert calculate("sqrt(144)") == "12"
    assert calculate("factorial(5)") == "120"
    assert calculate("abs(-7)") == "7"
    assert calculate("max(3, 9, 5)") == "9"
    # pi is available and formatted cleanly.
    assert calculate("round(pi, 2)") == "3.14"


def test_integer_vs_float_formatting():
    assert calculate("6/2") == "3"          # exact -> int form
    assert calculate("7/2") == "3.5"
    assert calculate("2.0 + 2.0") == "4"


# ---------------------------------------------------------------------------
# Security — must reject and NOT execute
# ---------------------------------------------------------------------------
def test_rejects_import_and_system(tmp_path):
    marker = tmp_path / "pwned.txt"
    payload = f"__import__('os').system('echo x > {marker}')"
    assert calculate(payload) is None
    assert not marker.exists()  # nothing was executed


def test_rejects_dunder_and_attribute_access():
    assert calculate("().__class__") is None
    assert calculate("(1).__class__.__bases__") is None
    assert calculate("os.system('x')") is None


def test_rejects_eval_open_lambda_comprehension():
    assert calculate("eval('1')") is None
    assert calculate("open('x')") is None
    assert calculate("lambda: 1") is None
    assert calculate("[i for i in range(10)]") is None
    assert calculate("{1: 2}") is None


def test_rejects_unknown_names():
    assert calculate("foo + 1") is None
    assert calculate("x") is None


# ---------------------------------------------------------------------------
# Robustness / DoS guards
# ---------------------------------------------------------------------------
def test_division_by_zero_is_none():
    assert calculate("1/0") is None
    assert calculate("5 % 0") is None


def test_dos_guards_do_not_hang():
    # Absurd exponent and factorial are rejected quickly, not computed.
    assert calculate("10**100000") is None
    assert calculate("factorial(99999)") is None


def test_nested_pow_chain_is_rejected():
    """Regression test for the 2026-08-23 deep scan finding: a single-level
    exponent cap alone is bypassable by chaining allowed exponentiations --
    (2**999)**999 has an exponent of 999 (passes an exponent-only check) but
    a base that's already ~999 bits, so computing it builds a ~998,000-bit
    integer. Live-tested in the original report: a 3-level chain took 7.46s
    and built a ~125MB integer with no error."""
    import time

    t0 = time.monotonic()
    assert calculate("((2**999)**999)**999") is None
    assert time.monotonic() - t0 < 1.0


def test_pow_function_bypass_is_rejected():
    """The pow() builtin (exposed in _FUNCS) is a second path to
    exponentiation that doesn't go through ast.Pow/** at all -- must get the
    same base-aware guard, not just the operator path."""
    assert calculate("pow(pow(2, 999), 999)") is None
    assert calculate("pow(2, 10)") == "1024"


def test_single_level_large_pow_still_allowed():
    # A single large-but-bounded exponentiation is legitimate and must still work.
    result = calculate("2**999")
    assert result is not None
    assert result.startswith("5357543035931336604")


def test_garbage_and_empty():
    assert calculate("") is None
    assert calculate("   ") is None
    assert calculate("not an expression!!") is None
    assert calculate(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# looks_like_math heuristic
# ---------------------------------------------------------------------------
def test_looks_like_math():
    assert looks_like_math("what is 45 * 12?")
    assert looks_like_math("2+2")
    assert looks_like_math("sqrt(50)")
    assert not looks_like_math("Barka da yamma, yaya kake?")
    assert not looks_like_math("")
