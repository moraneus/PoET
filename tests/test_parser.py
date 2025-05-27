# tests/test_parser.py

import pytest
from parser.parser import parse
from parser.ast import (
    Proposition, Constant, Not, And, Or, Implies, Iff,
    EY, AY, EP, AP, EH, AH, ES, AS, Paren
)

class TestParser:

    # --- Basic Propositions and Constants ---
    def test_parse_simple_proposition(self):
        result = parse("p")
        assert isinstance(result, Proposition) and result.proposition == "p"

    def test_parse_proposition_with_numbers(self):
        result = parse("p1")
        assert isinstance(result, Proposition) and result.proposition == "p1"

    def test_parse_true_constant(self):
        result = parse("TRUE")
        assert isinstance(result, Constant) and result.constant is True

    def test_parse_false_constant(self):
        result = parse("FALSE")
        assert isinstance(result, Constant) and result.constant is False

    # --- Unary Operators (Using the provided grammar) ---
    def test_parse_not(self):
        result = parse("!p")
        assert isinstance(result, Not)

    def test_parse_ey_with_parens(self):
        # Your grammar for EY/AY is `OP formula`, so it can take `p` or `(p)`
        result = parse("EY(p)")
        assert isinstance(result, EY)
        assert isinstance(result.formula, Paren)

    def test_parse_ay_no_parens(self):
        result = parse("AY p")
        assert isinstance(result, AY)
        assert isinstance(result.formula, Proposition)

    def test_parse_ep(self):
        result = parse("EP p")
        assert isinstance(result, EP)

    def test_parse_ap(self):
        result = parse("AP p")
        assert isinstance(result, AP)

    def test_parse_eh(self):
        result = parse("EH p")
        assert isinstance(result, EH)

    def test_parse_ah(self):
        result = parse("AH p")
        assert isinstance(result, AH)

    # --- Binary Operators ---
    def test_parse_and(self):
        result = parse("p & q")
        assert isinstance(result, And)

    def test_parse_or(self):
        result = parse("p | q")
        assert isinstance(result, Or)

    def test_parse_implies(self):
        result = parse("p -> q")
        assert isinstance(result, Implies)

    def test_parse_iff(self):
        result = parse("p <-> q")
        assert isinstance(result, Iff)

    def test_parse_e_since(self):
        result = parse("E(p S q)")
        assert isinstance(result, ES)

    def test_parse_a_since(self):
        result = parse("A(p S q)")
        assert isinstance(result, AS)

    # --- Complex Formulas and Precedence ---
    def test_parse_complex_formula_1(self):
        # Test structure, not just top-level type
        formula = "AH (p1 -> EP (q & r))"
        result = parse(formula)
        assert isinstance(result, AH)
        assert isinstance(result.formula, Paren)
        inner_implies = result.formula.formula
        assert isinstance(inner_implies, Implies)
        assert isinstance(inner_implies.formula2, EP)

    def test_parse_heavy_nesting(self):
        formula = "EY AY EH !p"
        result = parse(formula)
        assert isinstance(result, EY)
        assert isinstance(result.formula, AY)
        assert isinstance(result.formula.formula, EH)
        assert isinstance(result.formula.formula.formula, Not)

    def test_parse_precedence_or_and(self):
        result = parse("p | q & r")
        assert isinstance(result, Or)
        assert isinstance(result.formula2, And)

    def test_parse_left_associativity_of_implies(self):
        # Check the structure to confirm left-associativity: (p -> q) -> r
        result = parse("p -> q -> r")
        assert isinstance(result, Implies)

        # Check the left-hand side, which should be the expression (p -> q)
        lhs = result.formula1
        assert isinstance(lhs, Implies)
        assert isinstance(lhs.formula1, Proposition) and lhs.formula1.proposition == 'p'
        assert isinstance(lhs.formula2, Proposition) and lhs.formula2.proposition == 'q'

        # Check the right-hand side, which should be the proposition 'r'
        rhs = result.formula2
        assert isinstance(rhs, Proposition) and rhs.proposition == 'r'

    # --- Invalid Syntax Tests ---
    def test_parse_invalid_syntax_missing_paren(self):
        with pytest.raises(SystemExit):
            parse("A(p S q")

    def test_parse_invalid_syntax_dangling_op(self):
        with pytest.raises(SystemExit):
            parse("p &")

    def test_parse_invalid_syntax_misplaced_op(self):
        with pytest.raises(SystemExit):
            parse("p q &")