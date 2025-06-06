# tests/parser_tests/test_parser.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Unit tests for PCTL parser functionality, validating correct parsing of temporal operators,
# logical connectives, precedence rules, and error handling for invalid syntax.

import pytest
from parser.parser import parse
from parser.ast import (
    Proposition,
    Constant,
    Not,
    And,
    Or,
    Implies,
    Iff,
    EY,
    AY,
    EP,
    AP,
    EH,
    AH,
    ES,
    AS,
    Paren,
)


class TestParser:
    """Test suite for PCTL parser functionality."""

    def test_parse_simple_proposition(self):
        """Test parsing of basic proposition."""
        result = parse("p")
        assert isinstance(result, Proposition) and result.proposition == "p"

    def test_parse_proposition_with_numbers(self):
        """Test parsing of proposition with numeric suffix."""
        result = parse("p1")
        assert isinstance(result, Proposition) and result.proposition == "p1"

    def test_parse_true_constant(self):
        """Test parsing of TRUE constant."""
        result = parse("TRUE")
        assert isinstance(result, Constant) and result.constant is True

    def test_parse_false_constant(self):
        """Test parsing of FALSE constant."""
        result = parse("FALSE")
        assert isinstance(result, Constant) and result.constant is False

    def test_parse_not(self):
        """Test parsing of logical negation."""
        result = parse("!p")
        assert isinstance(result, Not)

    def test_parse_ey_with_parens(self):
        """Test parsing of EY operator with parentheses."""
        result = parse("EY(p)")
        assert isinstance(result, EY)
        assert isinstance(result.formula, Paren)

    def test_parse_ay_no_parens(self):
        """Test parsing of AY operator without parentheses."""
        result = parse("AY p")
        assert isinstance(result, AY)
        assert isinstance(result.formula, Proposition)

    def test_parse_ep(self):
        """Test parsing of EP (exists previously) operator."""
        result = parse("EP p")
        assert isinstance(result, EP)

    def test_parse_ap(self):
        """Test parsing of AP (always previously) operator."""
        result = parse("AP p")
        assert isinstance(result, AP)

    def test_parse_eh(self):
        """Test parsing of EH (exists historically) operator."""
        result = parse("EH p")
        assert isinstance(result, EH)

    def test_parse_ah(self):
        """Test parsing of AH (always historically) operator."""
        result = parse("AH p")
        assert isinstance(result, AH)

    def test_parse_and(self):
        """Test parsing of logical AND operator."""
        result = parse("p & q")
        assert isinstance(result, And)

    def test_parse_or(self):
        """Test parsing of logical OR operator."""
        result = parse("p | q")
        assert isinstance(result, Or)

    def test_parse_implies(self):
        """Test parsing of logical implication operator."""
        result = parse("p -> q")
        assert isinstance(result, Implies)

    def test_parse_iff(self):
        """Test parsing of logical biconditional operator."""
        result = parse("p <-> q")
        assert isinstance(result, Iff)

    def test_parse_e_since(self):
        """Test parsing of E(p S q) (exists since) operator."""
        result = parse("E(p S q)")
        assert isinstance(result, ES)

    def test_parse_a_since(self):
        """Test parsing of A(p S q) (always since) operator."""
        result = parse("A(p S q)")
        assert isinstance(result, AS)

    def test_parse_complex_nested_formula(self):
        """Test parsing of complex nested formula structure."""
        formula = "AH (p1 -> EP (q & r))"
        result = parse(formula)
        assert isinstance(result, AH)
        assert isinstance(result.formula, Paren)

        inner_implies = result.formula.formula
        assert isinstance(inner_implies, Implies)
        assert isinstance(inner_implies.formula2, EP)

    def test_parse_heavy_temporal_nesting(self):
        """Test parsing of heavily nested temporal operators."""
        formula = "EY AY EH !p"
        result = parse(formula)
        assert isinstance(result, EY)
        assert isinstance(result.formula, AY)
        assert isinstance(result.formula.formula, EH)
        assert isinstance(result.formula.formula.formula, Not)

    def test_parse_operator_precedence(self):
        """Test operator precedence: OR has lower precedence than AND."""
        result = parse("p | q & r")
        assert isinstance(result, Or)
        assert isinstance(result.formula2, And)

    def test_parse_implies_left_associativity(self):
        """Test left-associativity of implication: (p -> q) -> r."""
        result = parse("p -> q -> r")
        assert isinstance(result, Implies)

        lhs = result.formula1
        assert isinstance(lhs, Implies)
        assert isinstance(lhs.formula1, Proposition) and lhs.formula1.proposition == "p"
        assert isinstance(lhs.formula2, Proposition) and lhs.formula2.proposition == "q"

        rhs = result.formula2
        assert isinstance(rhs, Proposition) and rhs.proposition == "r"

    def test_parse_invalid_missing_parenthesis(self):
        """Test error handling for missing closing parenthesis."""
        with pytest.raises(SystemExit):
            parse("A(p S q")

    def test_parse_invalid_dangling_operator(self):
        """Test error handling for dangling binary operator."""
        with pytest.raises(SystemExit):
            parse("p &")

    def test_parse_invalid_misplaced_operator(self):
        """Test error handling for misplaced operators."""
        with pytest.raises(SystemExit):
            parse("p q &")
