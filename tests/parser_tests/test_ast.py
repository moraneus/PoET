# tests/parser_tests/test_ast.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Unit tests for AST evaluation logic, testing PCTL temporal operators and logical connectives
# against mock state objects with proposition assignments and predecessor state histories.

import pytest
from parser.parser import parse, Formula
from parser.ast import Proposition, Not, EP, AP


class MockState:
    """Mock state class for testing AST evaluation without full State dependencies."""

    def __init__(self, propositions, formula_obj, pre_summaries=None):
        self._propositions = set(propositions)
        subformulas = Formula.collect_formulas(formula_obj)
        self.now = {f: False for f in subformulas}

        self.pre = {}
        if pre_summaries:
            for pred_name, summary_dict in pre_summaries.items():
                complete_summary = {f: False for f in subformulas}
                complete_summary.update(summary_dict)
                self.pre[pred_name] = complete_summary

    def __contains__(self, prop):
        return prop in self._propositions

    def __str__(self):
        return f"MockState(props={self._propositions}, pre={self.pre}, now={self.now})"


class TestAST:
    """Test suite for AST node evaluation methods."""

    def test_eval_proposition_true(self):
        """Test proposition evaluation when true."""
        ast = parse("p")
        state = MockState(["p", "q"], ast)
        assert ast.eval(state=state) is True
        assert state.now["p"] is True

    def test_eval_constant_true(self):
        """Test TRUE constant evaluation."""
        ast = parse("TRUE")
        state = MockState([], ast)
        assert ast.eval(state=state) is True
        assert state.now.get("True", state.now.get("TRUE")) is True

    def test_eval_and_true(self):
        """Test logical AND when both operands are true."""
        ast = parse("p & q")
        state = MockState(["p", "q"], ast)
        assert ast.eval(state=state) is True
        assert state.now["p & q"] is True

    def test_eval_or_true(self):
        """Test logical OR when one operand is true."""
        ast = parse("p | q")
        state = MockState(["p"], ast)
        assert ast.eval(state=state) is True
        assert state.now["p | q"] is True

    def test_eval_not_true(self):
        """Test logical NOT when operand is false."""
        ast = parse("!p")
        state = MockState([], ast)
        assert ast.eval(state=state) is True
        assert state.now["! p"] is True

    def test_eval_not_false(self):
        """Test logical NOT when operand is true."""
        ast = parse("!p")
        state = MockState(["p"], ast)
        assert ast.eval(state=state) is False
        assert state.now["! p"] is False

    def test_eval_ey_true(self):
        """Test EY (exists yesterday) when formula held in predecessor."""
        ast = parse("EY(p)")
        pre_summaries = {"S1": {str(ast.formula): True}}
        state = MockState(["q"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ey_false(self):
        """Test EY when formula did not hold in any predecessor."""
        ast = parse("EY(p)")
        pre_summaries = {"S1": {str(ast.formula): False}}
        state = MockState(["q"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ay_true(self):
        """Test AY (always yesterday) when formula held in all predecessors."""
        ast = parse("AY(p)")
        pre_summaries = {"S1": {str(ast.formula): True}, "S2": {str(ast.formula): True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ay_false(self):
        """Test AY when formula failed in at least one predecessor."""
        ast = parse("AY p")
        pre_summaries = {
            "S1": {str(ast.formula): True},
            "S2": {str(ast.formula): False},
        }
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ep_true_current_state(self):
        """Test EP (exists previously) true when formula holds now."""
        ast = parse("EP(p)")
        state = MockState(["p"], ast, pre_summaries={"S1": {str(ast): False}})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ep_true_from_predecessor(self):
        """Test EP true when it held in a predecessor state."""
        ast = parse("EP(p)")
        pre_summaries = {"S1": {str(ast): True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ep_false(self):
        """Test EP false when formula never held."""
        ast = parse("EP(p)")
        pre_summaries = {"S1": {str(ast): False, str(ast.formula): False}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ep_false_no_predecessors(self):
        """Test EP false with no predecessors and formula false now."""
        ast = parse("EP(p)")
        state = MockState([], ast, pre_summaries={})
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ap_true_current_state(self):
        """Test AP (always previously) true when formula holds now."""
        ast = parse("AP(p)")
        state = MockState(["p"], ast, pre_summaries={"S1": {str(ast): False}})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ap_true_all_predecessors(self):
        """Test AP true when it held in all predecessor states."""
        ast = parse("AP(p)")
        pre_summaries = {"S1": {str(ast): True}, "S2": {str(ast): True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ap_false(self):
        """Test AP false when it failed in at least one predecessor."""
        ast = parse("AP(p)")
        pre_summaries = {
            "S1": {str(ast): True},
            "S2": {str(ast): False, str(ast.formula): False},
        }
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ap_true_no_predecessors(self):
        """Test AP true with no predecessors (vacuously true past)."""
        ast = parse("AP(p)")
        state = MockState([], ast, pre_summaries={})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_eh_false_when_p_true_no_history(self):
        """Test EH(p) = ¬AP(¬p) evaluates false when p true now, no predecessors."""
        ast = parse("EH(p)")
        state = MockState(["p"], ast, pre_summaries={})
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_eh_true_when_ap_not_p_false(self):
        """Test EH(p) true when AP(¬p) was false in a predecessor."""
        ast = parse("EH(p)")
        not_p_formula = Not(ast.formula)
        ap_not_p_formula = AP(not_p_formula)
        str_ap_not_p = str(ap_not_p_formula)

        pre_summaries = {"S1": {str_ap_not_p: False}}
        state = MockState(["p"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_eh_false_when_p_false_now(self):
        """Test EH(p) false when p is false now."""
        ast = parse("EH(p)")
        state = MockState([], ast, pre_summaries={})
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ah_true_when_ep_not_p_false(self):
        """Test AH(p) = ¬EP(¬p) true when EP(¬p) false in past."""
        ast = parse("AH(p)")
        ep_not_p_str = str(EP(Not(ast.formula)))

        pre_summaries = {"S1": {ep_not_p_str: False, str(Not(ast.formula)): False}}
        state = MockState(["p"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ah_false_when_not_p_now(self):
        """Test AH(p) false when ¬p holds now."""
        ast = parse("AH(p)")
        state = MockState([], ast, pre_summaries={})
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_ah_false_when_ep_not_p_true_past(self):
        """Test AH(p) false when EP(¬p) was true in past."""
        ast = parse("AH(p)")
        ep_not_p_str = str(EP(Not(ast.formula)))

        pre_summaries = {"S1": {ep_not_p_str: True}}
        state = MockState(["p"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_e_since_from_current_q(self):
        """Test E(p S q) true when q holds now."""
        ast = parse("E(p S q)")
        state = MockState(["q"], ast)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_e_since_from_path(self):
        """Test E(p S q) true when it held in predecessor path."""
        ast = parse("E(p S q)")
        pre_summaries = {"S1": {str(ast): True}}
        state = MockState(["p"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_a_since_fail_from_path(self):
        """Test A(p S q) false when it failed in some predecessor path."""
        ast = parse("A(p S q)")
        pre_summaries = {
            "S1": {str(ast): True, str(ast.formula1): True, str(ast.formula2): False},
            "S2": {str(ast): False, str(ast.formula1): True, str(ast.formula2): False},
        }
        state = MockState(["p"], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False
        assert state.now[str(ast)] is False

    def test_eval_paren_evaluates_inner(self):
        """Test parentheses evaluation delegates to inner formula."""
        ast = parse("(p)")
        state = MockState(["p"], ast)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ep_simple_prop_true_now(self):
        """Test EP with simple proposition true now."""
        ast = parse("EP p")
        state = MockState(["p"], ast, pre_summaries={})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ep_simple_prop_true_past(self):
        """Test EP with simple proposition true in past."""
        ast = parse("EP p")
        pre_summaries = {"S1": {str(ast): True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ap_simple_prop_true_now(self):
        """Test AP with simple proposition true now."""
        ast = parse("AP p")
        state = MockState(["p"], ast, pre_summaries={})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_ap_simple_prop_true_past(self):
        """Test AP with simple proposition true in all past states."""
        ast = parse("AP p")
        pre_summaries = {"S1": {str(ast): True}, "S2": {str(ast): True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_nested_temporal_ep_ap_true_now(self):
        """Test nested EP(AP(p)) when AP(p) is true now."""
        ast = parse("EP(AP(p))")
        state = MockState(["p"], ast, pre_summaries={})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_nested_temporal_ep_ap_true_past_ap(self):
        """Test EP(AP(p)) when AP(p) is true due to current state."""
        ast = parse("EP(AP(p))")
        state = MockState(["p"], ast, pre_summaries={})
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True

    def test_eval_nested_temporal_ep_ap_true_past_ep(self):
        """Test EP(AP(p)) when EP(AP(p)) was true in predecessor."""
        ast = parse("EP(AP(p))")
        ap_p_str = str(ast.formula)
        pre_summaries = {"S1": {str(ast): True, ap_p_str: False}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True
        assert state.now[str(ast)] is True
