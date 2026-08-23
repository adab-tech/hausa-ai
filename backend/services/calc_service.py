"""
Safe arithmetic evaluator — exact calculations for Murya, without the LLM's
unreliable mental math.

Security is the whole point: this NEVER uses eval()/exec(). It parses the
expression with `ast` and walks the tree against a strict allow-list, so an
input like "__import__('os').system(...)" is rejected as un-evaluatable
rather than executed. Anything outside the allow-list -> None.

Stdlib only: ast, math, operator.
"""

from __future__ import annotations

import ast
import math
import operator

# Binary and unary operators we permit.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Named constants.
_NAMES: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

# Callable allow-list (name -> function).
_FUNCS = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "exp": math.exp,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "degrees": math.degrees,
    "radians": math.radians,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "pow": pow,
    "min": min,
    "max": max,
    "hypot": math.hypot,
    "fabs": math.fabs,
}

# DoS guards: reject expressions that would hang or exhaust memory.
_MAX_POW_EXPONENT = 1000
_MAX_FACTORIAL = 1000
# ~1233 decimal digits -- far beyond any sane calculator answer, but small
# enough that even the worst-case allowed computation stays instant.
_MAX_RESULT_BITS = 4096


class _Unsafe(Exception):
    """Raised internally when a node/operation is outside the allow-list."""


def _bit_length(value: float | int) -> int:
    if isinstance(value, int):
        return abs(value).bit_length()
    if isinstance(value, float) and value == value and abs(value) not in (math.inf,):
        return abs(value).__trunc__().bit_length() if abs(value) < 1e300 else _MAX_RESULT_BITS + 1
    return 0


def _check_pow(base: float | int, exponent: float | int) -> None:
    """Reject an exponentiation before it runs, not after. A literal exponent
    cap alone isn't enough: (2**999)**999 has an exponent of 999 (passes a
    exponent-only check) but its base is already ~999 bits from the first,
    individually-allowed exponentiation -- computing it builds a ~998,000-bit
    integer. Estimate the result's bit-length from the base's bit-length
    instead of waiting to see how big the actual result turns out to be."""
    if abs(exponent) > _MAX_POW_EXPONENT:
        raise _Unsafe("exponent too large")
    if exponent and _bit_length(base) * abs(float(exponent)) > _MAX_RESULT_BITS:
        raise _Unsafe("result too large")


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _Unsafe("only int/float literals allowed")
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise _Unsafe("operator not allowed")
        left = _eval(node.left)
        right = _eval(node.right)
        if op_type is ast.Pow:
            _check_pow(left, right)
        result = _BIN_OPS[op_type](left, right)
        if _bit_length(result) > _MAX_RESULT_BITS:
            raise _Unsafe("result too large")
        return result

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise _Unsafe("unary operator not allowed")
        return _UNARY_OPS[op_type](_eval(node.operand))

    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise _Unsafe(f"name '{node.id}' not allowed")

    if isinstance(node, ast.Call):
        # Only bare-name calls from the allow-list; no attributes, no kwargs.
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise _Unsafe("function not allowed")
        if node.keywords:
            raise _Unsafe("keyword arguments not allowed")
        name = node.func.id
        args = [_eval(a) for a in node.args]
        if name == "factorial":
            n = args[0]
            if not isinstance(n, int) or n < 0 or n > _MAX_FACTORIAL:
                raise _Unsafe("factorial out of range")
        if name == "pow" and len(args) >= 2:
            # The pow() builtin is a second path to exponentiation that
            # bypasses the ast.Pow/** guard above entirely -- same estimate
            # check before computing.
            _check_pow(args[0], args[1])
        result = _FUNCS[name](*args)
        if _bit_length(result) > _MAX_RESULT_BITS:
            raise _Unsafe("result too large")
        return result

    # Anything else (Attribute, Subscript, Lambda, comprehensions, ...) is banned.
    raise _Unsafe(f"disallowed expression: {type(node).__name__}")


def _format(value: float | int) -> str:
    """Render a numeric result cleanly: ints as ints, floats trimmed to a
    sensible precision with no trailing zeros."""
    if isinstance(value, bool):  # defensive; bools are rejected upstream
        raise _Unsafe("bool result")
    if isinstance(value, int):
        return str(value)
    if value != value or value in (math.inf, -math.inf):  # NaN / inf
        raise _Unsafe("non-finite result")
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.10g}"


def calculate(expression: str) -> str | None:
    """Evaluate `expression` safely and return the result as a string, or None
    if it is not a valid, safe, finite arithmetic expression. Never raises,
    never executes arbitrary code."""
    if not isinstance(expression, str) or not expression.strip():
        return None
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval(tree.body)
        return _format(result)
    except (_Unsafe, SyntaxError, ValueError, TypeError,
            ZeroDivisionError, OverflowError, RecursionError, MemoryError):
        return None


# Operators/keywords that signal an arithmetic intent.
_MATH_HINT = ("+", "-", "*", "/", "%", "^", "(", ")")
_FUNC_HINT = tuple(_FUNCS.keys())


def looks_like_math(text: str) -> bool:
    """Conservative heuristic: True when `text` plausibly contains an
    arithmetic expression worth computing. False negatives are fine — a false
    positive just makes calculate() return None and nothing is injected."""
    if not isinstance(text, str):
        return False
    low = text.lower()
    has_digit = any(c.isdigit() for c in text)
    has_op = any(sym in text for sym in _MATH_HINT if sym not in "()")
    has_func = any(fn + "(" in low for fn in _FUNC_HINT)
    return (has_digit and has_op) or has_func
