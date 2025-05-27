# tests/test_ast.py

import pytest
from parser.parser import parse, Formula


# Mock State class to simulate the real State object for testing purposes
class MockState:
    def __init__(self, propositions, formula_obj, pre_summaries=None):
        self._propositions = set(propositions)
        # Generate subformulas directly from the AST for accuracy
        subformulas = Formula.collect_formulas(formula_obj)
        self.now = {f: False for f in subformulas}
        # Ensure the pre-summaries are complete for what eval might look for
        self.pre = pre_summaries if pre_summaries is not None else {}

    def __contains__(self, prop):
        return prop in self._propositions


class TestAST:

    # --- Proposition and Constant Tests ---
    def test_eval_proposition_true(self):
        ast = parse("p")
        state = MockState(['p', 'q'], ast)
        assert ast.eval(state=state) is True

    def test_eval_constant_true(self):
        ast = parse("TRUE")
        state = MockState([], ast)
        assert ast.eval(state=state) is True
        assert state.now['True'] is True  # Note: str(True) is 'True', not 'TRUE'

    # --- Logical Operator Tests ---
    def test_eval_and_true(self):
        ast = parse("p & q")
        state = MockState(['p', 'q'], ast)
        assert ast.eval(state=state) is True

    def test_eval_or_true(self):
        ast = parse("p | q")
        state = MockState(['p'], ast)
        assert ast.eval(state=state) is True

    def test_eval_not_true(self):
        ast = parse("!p")
        state = MockState([], ast)
        assert ast.eval(state=state) is True
        assert state.now['! p'] is True  # Note the space from the __str__ method

    def test_eval_not_false(self):
        ast = parse("!p")
        state = MockState(['p'], ast)
        assert ast.eval(state=state) is False
        assert state.now['! p'] is False

    # --- Temporal Operator Tests (crafted to match SUT's logic) ---
    def test_eval_ey_true(self):
        # The parser turns 'EY(p)' into EY(Paren(p)). The eval for EY looks for
        # the __str__ of the inner formula, which is '(p)'.
        ast = parse("EY(p)")
        pre_summaries = {'S1': {'(p)': True}}
        state = MockState(['q'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_ey_false(self):
        ast = parse("EY(p)")
        pre_summaries = {'S1': {'(p)': False}}
        state = MockState(['q'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_ay_true(self):
        ast = parse("AY(p)")
        pre_summaries = {'S1': {'(p)': True}, 'S2': {'(p)': True}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_ay_false(self):
        ast = parse("AY p")  # Use syntax without parens
        pre_summaries = {'S1': {'p': True}, 'S2': {'p': False}}
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_ep_from_predecessor(self):
        # EP's eval looks for its own __str__ in the history.
        ast = parse("EP(p)")
        pre_summaries = {'S1': {'EP((p))': True}}  # Note the double parens from parsing
        state = MockState([], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_ep_from_current(self):
        ast = parse("EP(p)")
        pre_summaries = {'S1': {'EP((p))': False}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_ep_false(self):
        ast = parse("EP(p)")
        pre_summaries = {'S1': {'EP((p))': False}}
        state = MockState(['q'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_ah_from_current_and_predecessor(self):
        ast = parse("AH(p)")
        pre_summaries = {'S1': {'AH((p))': True}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_ah_fail_from_predecessor(self):
        ast = parse("AH(p)")
        pre_summaries = {'S1': {'AH((p))': False}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_e_since_from_current_q(self):
        ast = parse("E(p S q)")
        state = MockState(['q'], ast)
        assert ast.eval(state=state) is True

    def test_eval_e_since_from_path(self):
        ast = parse("E(p S q)")
        pre_summaries = {'S1': {'E(p S q)': True}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_a_since_fail_from_path(self):
        ast = parse("A(p S q)")
        pre_summaries = {'S1': {'A(p S q)': True}, 'S2': {'A(p S q)': False}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_eh_true(self):
        ast = parse("EH(p)")
        pre_summaries = {'S0': {}, 'S1': {'EH((p))': True}}
        state = MockState(['p'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is True

    def test_eval_eh_false_if_prop_is_false(self):
        ast = parse("EH(p)")
        pre_summaries = {'S0': {}, 'S1': {'EH((p))': True}}
        state = MockState(['q'], ast, pre_summaries=pre_summaries)
        assert ast.eval(state=state) is False

    def test_eval_paren_evaluates_inner(self):
        ast = parse("(p)")
        state = MockState(['p'], ast)
        assert ast.eval(state=state) is True
        assert state.now['(p)'] is True