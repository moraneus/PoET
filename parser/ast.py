# parser/ast.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Abstract Syntax Tree classes for PCTL formula representation and evaluation,
# implementing past-time temporal logic operators over distributed system states.

import sys
from typing import List

from model.state import State


def error(msg: str) -> None:
    """Print error message and exit."""
    print(f"*** Error - {msg}")
    sys.exit(1)


class Formula:
    """Base class for all PCTL formula nodes."""

    def eval(self, **kwargs) -> bool:
        """Evaluate formula in given context."""
        pass

    @staticmethod
    def collect_formulas(formula: "Formula") -> List[str]:
        """Collect all subformulas from given formula tree."""
        formulas = []

        def recurse(f: "Formula") -> None:
            if isinstance(f, (Proposition, Constant)):
                formulas.append(str(f))
            elif isinstance(f, (And, Or, Implies, ES, AS, Iff)):
                formulas.append(str(f))
                recurse(f.formula1)
                recurse(f.formula2)
            elif isinstance(f, (Not, EY, AY, EP, AP, AH, EH)):
                formulas.append(str(f))
                recurse(f.formula)
            elif isinstance(f, Paren):
                formulas.append(str(f))
                recurse(f.formula)
            else:
                print(f"Unhandled type: {type(f)}")

        recurse(formula)
        return formulas


class Proposition(Formula):
    """Atomic proposition formula."""

    def __init__(self, proposition: str):
        self.proposition = proposition

    def __str__(self) -> str:
        return self.proposition

    def __repr__(self) -> str:
        return f"{repr(self.proposition)}"

    def eval(self, **kwargs) -> bool:
        """Evaluate proposition in current state."""
        evaluated_state: State = kwargs["state"]
        res = self.proposition in evaluated_state
        evaluated_state.now[self.__str__()] = res
        return res


class And(Formula):
    """Logical AND formula."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"{self.formula1} & {self.formula2}"

    def __repr__(self) -> str:
        return f"&({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate logical AND of two formulas."""
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = p and q
        evaluated_state.now[self.__str__()] = res
        return res


class Or(Formula):
    """Logical OR formula."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"{self.formula1} | {self.formula2}"

    def __repr__(self) -> str:
        return f"|({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate logical OR of two formulas."""
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = p or q
        evaluated_state.now[self.__str__()] = res
        return res


class Implies(Formula):
    """Logical implication formula."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"{self.formula1} -> {self.formula2}"

    def __repr__(self) -> str:
        return f"->({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate logical implication."""
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = (not p) or q
        evaluated_state.now[self.__str__()] = res
        return res


class Iff(Formula):
    """Logical biconditional formula."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"{self.formula1} <-> {self.formula2}"

    def __repr__(self) -> str:
        return f"<->({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate logical biconditional."""
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = ((not p) or q) and ((not q) or p)
        evaluated_state.now[self.__str__()] = res
        return res


class Not(Formula):
    """Logical negation formula."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"! {self.formula}"

    def __repr__(self) -> str:
        return f"!({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate logical negation."""
        evaluated_state: State = kwargs["state"]
        p = self.formula.eval(**kwargs)
        res = not p
        evaluated_state.now[self.__str__()] = res
        return res


class EY(Formula):
    """Existential yesterday temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"EY({self.formula})"

    def __repr__(self) -> str:
        return f"EY({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate existential yesterday: true if formula held in some predecessor."""
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        evaluated_state: State = kwargs["state"]
        self.formula.eval(**kwargs)

        temporal_res = False
        sub_formula_str = str(self.formula)

        for _, summary in evaluated_state.pre.items():
            if summary.get(sub_formula_str, False):
                temporal_res = True
                break

        evaluated_state.now[self.__str__()] = temporal_res
        return temporal_res


class AY(Formula):
    """Universal yesterday temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"AY({self.formula})"

    def __repr__(self) -> str:
        return f"AY({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate universal yesterday: true if formula held in all predecessors.

        AY φ = ¬EY ¬φ, so AY φ is vacuously true when there are no predecessors.
        """
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        evaluated_state: State = kwargs["state"]
        self.formula.eval(**kwargs)

        temporal_res = True
        sub_formula_str = str(self.formula)

        if evaluated_state.pre:
            for _, summary in evaluated_state.pre.items():
                if not summary.get(sub_formula_str, False):
                    temporal_res = False
                    break

        evaluated_state.now[self.__str__()] = temporal_res
        return temporal_res


class EP(Formula):
    """Existential previously temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"EP({self.formula})"

    def __repr__(self) -> str:
        return f"EP({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate existential previously: E(true S φ).

        EP φ holds if φ holds now OR EP φ held in some predecessor.
        """
        evaluated_state: State = kwargs["state"]

        holds_now = self.formula.eval(**kwargs)
        held_in_past = False
        ep_formula_str = str(self)

        for _, summary in evaluated_state.pre.items():
            if summary.get(ep_formula_str, False):
                held_in_past = True
                break

        res = holds_now or held_in_past
        evaluated_state.now[ep_formula_str] = res
        return res


class AP(Formula):
    """Universal previously temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"AP({self.formula})"

    def __repr__(self) -> str:
        return f"AP({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate universal previously: A(true S φ).

        According to the paper's semantics:
        S |= A(φSψ) if either S |= ψ or both S |= φ and for each S' ↠ S
        it holds that S' |= A(φSψ), where at least one such predecessor S' exists.

        For AP φ = A(true S φ):
        - At initial state (no predecessors): AP φ holds iff φ holds now
        - Otherwise: AP φ holds iff φ holds now OR AP φ held in all predecessors
        """
        evaluated_state: State = kwargs["state"]

        holds_now = self.formula.eval(**kwargs)
        ap_formula_str = str(self)

        # The second disjunct requires at least one predecessor to exist
        held_in_all_past = False

        if evaluated_state.pre:
            # Only if predecessors exist, check if AP held in all of them
            held_in_all_past = True
            for _, summary in evaluated_state.pre.items():
                if not summary.get(ap_formula_str, False):
                    held_in_all_past = False
                    break

        res = holds_now or held_in_all_past
        evaluated_state.now[ap_formula_str] = res
        return res


class EH(Formula):
    """Existential historically temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"EH({self.formula})"

    def __repr__(self) -> str:
        return f"EH({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate existential historically: ¬AP(¬φ)."""
        negated_formula = Not(self.formula)
        ap_of_negated = AP(negated_formula)

        res = not ap_of_negated.eval(**kwargs)
        self.formula.eval(**kwargs)

        evaluated_state: State = kwargs["state"]
        evaluated_state.now[self.__str__()] = res
        return res


class AH(Formula):
    """Universal historically temporal operator."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"AH({self.formula})"

    def __repr__(self) -> str:
        return f"AH({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate universal historically: ¬EP(¬φ)."""
        negated_formula = Not(self.formula)
        ep_of_negated = EP(negated_formula)

        res = not ep_of_negated.eval(**kwargs)
        self.formula.eval(**kwargs)

        evaluated_state: State = kwargs["state"]
        evaluated_state.now[self.__str__()] = res
        return res


class ES(Formula):
    """Existential since temporal operator."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"E({self.formula1} S {self.formula2})"

    def __repr__(self) -> str:
        return f"ES({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate existential since operator.

        S |= E(φSψ) if either S |= ψ or both S |= φ and there exists
        S' ↠ S such that S' |= E(φSψ).
        """
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        evaluated_state: State = kwargs["state"]

        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)

        temporal_res = False
        es_formula_str = str(self)

        for _, summary in evaluated_state.pre.items():
            if summary.get(es_formula_str, False):
                temporal_res = True
                break

        current_eval = q or (p and temporal_res)
        evaluated_state.now[es_formula_str] = current_eval
        return current_eval


class AS(Formula):
    """Universal since temporal operator."""

    def __init__(self, formula1: Formula, formula2: Formula):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self) -> str:
        return f"A({self.formula1} S {self.formula2})"

    def __repr__(self) -> str:
        return f"AS({repr(self.formula1)}, {repr(self.formula2)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate universal since operator.

        According to the paper's semantics:
        S |= A(φSψ) if either S |= ψ or both S |= φ and for each S' ↠ S
        it holds that S' |= A(φSψ), where at least one such predecessor S' exists.

        At initial state (no predecessors): A(φSψ) holds iff ψ holds now.
        """
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        evaluated_state: State = kwargs["state"]

        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)

        as_formula_str = str(self)

        # The second disjunct requires at least one predecessor to exist
        temporal_res = False

        if evaluated_state.pre:
            # Only if predecessors exist, check if AS held in all of them
            temporal_res = True
            for _, summary in evaluated_state.pre.items():
                if not summary.get(as_formula_str, False):
                    temporal_res = False
                    break

        current_eval = q or (p and temporal_res)
        evaluated_state.now[as_formula_str] = current_eval
        return current_eval


class Paren(Formula):
    """Parenthesized formula for grouping."""

    def __init__(self, formula: Formula):
        self.formula = formula

    def __str__(self) -> str:
        return f"({self.formula})"

    def __repr__(self) -> str:
        return f"({repr(self.formula)})"

    def eval(self, **kwargs) -> bool:
        """Evaluate parenthesized formula."""
        evaluated_state: State = kwargs["state"]
        res = self.formula.eval(**kwargs)
        evaluated_state.now[self.__str__()] = res
        return res


class Constant(Formula):
    """Boolean constant formula."""

    def __init__(self, constant: bool):
        self.constant = constant

    def __str__(self) -> str:
        return f"{self.constant}"

    def __repr__(self) -> str:
        return f"{repr(self.constant)}"

    def eval(self, **kwargs) -> bool:
        """Evaluate boolean constant."""
        evaluated_state: State = kwargs["state"]
        res = self.constant
        evaluated_state.now[self.__str__()] = res
        return res
