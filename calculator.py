#!/usr/bin/env python3
from __future__ import annotations

import ast
import math
import operator
import sys
import textwrap

try:
    import readline
except ImportError:
    pass

__version__ = "1.0.0"

PRECISION = 12
MAX_BITS = 14_000
MAX_FACTORIAL = 1_000


class CalculatorError(Exception):
    pass


def _power(base: int | float, exponent: int | float) -> int | float:
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0:
        if exponent * (abs(base).bit_length() - 1) > MAX_BITS:
            raise CalculatorError("Результат слишком велик")
    return base ** exponent


def _factorial(n: int | float) -> int:
    if isinstance(n, float) and n.is_integer():
        n = int(n)
    if not isinstance(n, int) or n < 0:
        raise CalculatorError("Факториал определён только для целых неотрицательных чисел")
    if n > MAX_FACTORIAL:
        raise CalculatorError(f"Слишком большой аргумент факториала (максимум {MAX_FACTORIAL})")
    return math.factorial(n)


def _ln(x: float) -> float:
    return math.log(x)


def _log(x: float, base: float = 10) -> float:
    if base == 10:
        return math.log10(x)
    return math.log(x, base)


BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: _power,
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "radians": math.radians,
    "degrees": math.degrees,
    "ln": _ln,
    "log": _log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": _factorial,
    "min": min,
    "max": max,
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _check(value):
    if isinstance(value, complex):
        raise CalculatorError("Результат — комплексное число (не поддерживается)")
    if isinstance(value, float) and not math.isfinite(value):
        raise CalculatorError("Результат слишком велик или не определён")
    if isinstance(value, int) and value.bit_length() > MAX_BITS:
        raise CalculatorError("Результат слишком велик")
    return value


def _eval(node: ast.AST, scope: dict):
    if isinstance(node, ast.Constant):
        if type(node.value) in (int, float):
            return _check(node.value)
        raise CalculatorError("Допускаются только числа")

    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left = _eval(node.left, scope)
        right = _eval(node.right, scope)
        return _check(BINARY_OPS[type(node.op)](left, right))

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return _check(UNARY_OPS[type(node.op)](_eval(node.operand, scope)))

    if isinstance(node, ast.Name):
        if node.id in scope:
            return scope[node.id]
        raise CalculatorError(f"Неизвестное имя: {node.id}")

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        function = FUNCTIONS.get(node.func.id)
        if function is None:
            raise CalculatorError(f"Неизвестная функция: {node.func.id}")
        arguments = [_eval(argument, scope) for argument in node.args]
        return _check(function(*arguments))

    if isinstance(node, ast.Tuple):
        raise CalculatorError("Для десятичных дробей используйте точку: 2.5, а не 2,5")

    raise CalculatorError("Недопустимое выражение")


def evaluate(expression: str, names: dict | None = None) -> int | float:
    text = (
        expression.replace("^", "**")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .strip()
    )
    if not text:
        raise CalculatorError("Пустое выражение")

    scope = {**CONSTANTS, **(names or {})}
    try:
        tree = ast.parse(text, mode="eval")
        return _eval(tree.body, scope)
    except SyntaxError as exc:
        raise CalculatorError("Синтаксическая ошибка в выражении") from exc
    except ZeroDivisionError as exc:
        raise CalculatorError("Деление на ноль") from exc
    except OverflowError as exc:
        raise CalculatorError("Результат слишком велик") from exc
    except ValueError as exc:
        raise CalculatorError("Значение вне области определения функции") from exc
    except TypeError as exc:
        raise CalculatorError("Неверное число аргументов функции") from exc
    except RecursionError as exc:
        raise CalculatorError("Слишком сложное выражение") from exc


def format_result(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.{PRECISION}g}"


USAGE = (
    "Использование:\n"
    '  python calculator.py "выражение"   вычислить и выйти\n'
    "  python calculator.py               интерактивный режим\n"
    "  python calculator.py --version     версия программы"
)


def _help_text() -> str:
    functions = textwrap.fill(
        ", ".join(sorted(FUNCTIONS)), width=68, initial_indent="  ", subsequent_indent="  "
    )
    return (
        "Операции: +  -  *  /  //  %  **  (или ^), скобки ( )\n"
        f"Функции:\n{functions}\n"
        f"Константы: {', '.join(sorted(CONSTANTS))}; ans — последний результат\n"
        "Примеры: 2 + 2 * 2 | sqrt(16) + 2^3 | sin(radians(30)) | ans * 2\n"
        "Команды: help — справка, exit / quit / q — выход"
    )


def run_repl() -> int:
    print(f"Калькулятор {__version__}. Введите выражение (help — справка, exit — выход).")
    last: int | float = 0
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit", "q"}:
            break
        if line.lower() in {"help", "?"}:
            print(_help_text())
            continue
        try:
            last = evaluate(line, {"ans": last})
        except CalculatorError as exc:
            print(f"Ошибка: {exc}")
        else:
            print(format_result(last))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)

    if args and args[0] in {"-h", "--help"}:
        print(USAGE + "\n\n" + _help_text())
        return 0
    if args and args[0] in {"-v", "--version"}:
        print(f"calculator {__version__}")
        return 0
    if not args:
        return run_repl()

    try:
        print(format_result(evaluate(" ".join(args))))
    except CalculatorError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
