import contextlib
import io
import math
import unittest
from unittest import mock

import calculator
from calculator import CalculatorError, evaluate, format_result, main


class ArithmeticTests(unittest.TestCase):
    def test_basic_operations(self):
        self.assertEqual(evaluate("2 + 3"), 5)
        self.assertEqual(evaluate("10 - 4"), 6)
        self.assertEqual(evaluate("6 * 7"), 42)
        self.assertEqual(evaluate("9 / 4"), 2.25)

    def test_operator_precedence(self):
        self.assertEqual(evaluate("2 + 2 * 2"), 6)
        self.assertEqual(evaluate("(2 + 2) * 2"), 8)
        self.assertEqual(evaluate("2 ** 3 ** 2"), 512)

    def test_floor_division_and_modulo(self):
        self.assertEqual(evaluate("7 // 2"), 3)
        self.assertEqual(evaluate("7 % 3"), 1)

    def test_unary_operators(self):
        self.assertEqual(evaluate("-5 + 3"), -2)
        self.assertEqual(evaluate("-2 ** 2"), -4)
        self.assertEqual(evaluate("+4"), 4)

    def test_caret_means_power(self):
        self.assertEqual(evaluate("2 ^ 10"), 1024)

    def test_unicode_operators(self):
        self.assertEqual(evaluate("6 × 7 ÷ 2 − 1"), 20)


class FunctionTests(unittest.TestCase):
    def test_sqrt(self):
        self.assertEqual(evaluate("sqrt(16)"), 4)

    def test_trigonometry(self):
        self.assertAlmostEqual(evaluate("sin(radians(30))"), 0.5)
        self.assertAlmostEqual(evaluate("cos(0)"), 1)

    def test_logarithms(self):
        self.assertEqual(evaluate("log(1000)"), 3)
        self.assertAlmostEqual(evaluate("log(8, 2)"), 3)
        self.assertAlmostEqual(evaluate("ln(e)"), 1)

    def test_rounding(self):
        self.assertEqual(evaluate("round(3.14159, 2)"), 3.14)
        self.assertEqual(evaluate("floor(2.7) + ceil(2.1)"), 5)

    def test_factorial(self):
        self.assertEqual(evaluate("factorial(5)"), 120)
        self.assertEqual(evaluate("factorial(5.0)"), 120)

    def test_min_max_abs(self):
        self.assertEqual(evaluate("max(1, 5, 3) - min(4, 2) + abs(-1)"), 4)


class ConstantsAndVariablesTests(unittest.TestCase):
    def test_constants(self):
        self.assertAlmostEqual(evaluate("pi"), math.pi)
        self.assertAlmostEqual(evaluate("2 * pi"), math.tau)

    def test_custom_variables(self):
        self.assertEqual(evaluate("ans * 2", {"ans": 21}), 42)


class ErrorTests(unittest.TestCase):
    def assertRejected(self, expression, fragment=None):
        with self.assertRaises(CalculatorError) as context:
            evaluate(expression)
        if fragment:
            self.assertIn(fragment, str(context.exception))

    def test_division_by_zero(self):
        for expression in ("1 / 0", "1 // 0", "1 % 0"):
            with self.subTest(expression=expression):
                self.assertRejected(expression, "Деление на ноль")

    def test_domain_errors(self):
        for expression in ("sqrt(-1)", "ln(0)", "asin(2)"):
            with self.subTest(expression=expression):
                self.assertRejected(expression)

    def test_syntax_errors(self):
        for expression in ("2 +", "(2 + 3", "2 +* 3"):
            with self.subTest(expression=expression):
                self.assertRejected(expression, "Синтаксическая")

    def test_empty_expression(self):
        self.assertRejected("   ", "Пустое")

    def test_unknown_names(self):
        self.assertRejected("foo + 1", "foo")
        self.assertRejected("foo(1)", "foo")

    def test_wrong_number_of_arguments(self):
        self.assertRejected("sqrt()")
        self.assertRejected("sqrt(1, 2)")

    def test_invalid_factorial(self):
        self.assertRejected("factorial(-1)")
        self.assertRejected("factorial(2.5)")

    def test_complex_result_is_rejected(self):
        self.assertRejected("(-8) ** 0.5", "комплексное")

    def test_decimal_comma_hint(self):
        self.assertRejected("2,5 + 1", "точку")


class SafetyTests(unittest.TestCase):
    def test_arbitrary_code_cannot_be_executed(self):
        for expression in (
            "__import__('os').system('echo hacked')",
            "().__class__.__bases__",
            "open('secret.txt')",
            "'abc' * 3",
            "[1, 2, 3]",
            "True + 1",
            "lambda: 1",
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate(expression)

    def test_huge_numbers_do_not_hang(self):
        for expression in (
            "9 ** 9 ** 9 ** 9",
            "10 ** 100000",
            "(10 ** 9999) ** 9999",
            "factorial(100000)",
            "1e308 * 10",
            "10.0 ** 1000",
            "1e999",
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate(expression)


class FormatTests(unittest.TestCase):
    def test_format_result(self):
        self.assertEqual(format_result(4), "4")
        self.assertEqual(format_result(4.0), "4")
        self.assertEqual(format_result(2.5), "2.5")
        self.assertEqual(format_result(1 / 3), "0.333333333333")
        self.assertEqual(format_result(10 ** 20), "1" + "0" * 20)

    def test_float_noise_is_hidden(self):
        self.assertEqual(format_result(evaluate("0.1 + 0.2")), "0.3")


class CommandLineTests(unittest.TestCase):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_expression_from_arguments(self):
        self.assertEqual(self.run_main("2", "+", "2", "*", "2"), (0, "6", ""))

    def test_negative_first_argument(self):
        self.assertEqual(self.run_main("-(2 + 3)"), (0, "-5", ""))

    def test_error_gives_nonzero_exit_code(self):
        code, out, err = self.run_main("1 / 0")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Деление на ноль", err)

    def test_version_and_help(self):
        code, out, _ = self.run_main("--version")
        self.assertEqual((code, out), (0, f"calculator {calculator.__version__}"))
        code, out, _ = self.run_main("--help")
        self.assertEqual(code, 0)
        self.assertIn("sqrt", out)

    def test_interactive_mode_remembers_last_result(self):
        inputs = ["2 + 2", "ans * 3", "1 / 0", "ans", "exit"]
        with mock.patch("builtins.input", side_effect=inputs):
            code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[1:], ["4", "12", "Ошибка: Деление на ноль", "12"])

    def test_interactive_mode_exits_on_eof(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            code, _, _ = self.run_main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
