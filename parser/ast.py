# parser/ast.py

import sys

from model.state import State


def error(msg: str):
    print(f'*** Error - {msg}')
    sys.exit(1)


class Formula:

    def eval(self, **kwargs):
        pass

    @staticmethod
    def collect_formulas(formula):
        formulas = []

        def recurse(f):
            # If the formula is a proposition or constant bool, add it directly to the list
            if isinstance(f, (Proposition, Constant)):
                formulas.append(str(f))
            # Handle binary operations
            elif isinstance(f, (And, Or, Implies, ES, AS, Iff)):
                formulas.append(str(f))
                recurse(f.formula1)
                recurse(f.formula2)
            # Handle unary operations
            elif isinstance(f, (Not, EY, AY, EP, AP, AH, EH)):
                formulas.append(str(f))
                recurse(f.formula)
            # Handle parenthesized formulas
            elif isinstance(f, Paren):
                formulas.append(str(f))
                recurse(f.formula)
            else:
                print(f"Unhandled type: {type(f)}")

        recurse(formula)
        return formulas


class Proposition(Formula):
    def __init__(self, proposition):
        self.proposition = proposition

    def __str__(self):
        return self.proposition

    def __repr__(self):
        return f'{repr(self.proposition)}'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        res = self.proposition in evaluated_state
        evaluated_state.now[self.__str__()] = res
        return res


class And(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'{self.formula1} & {self.formula2}'

    def __repr__(self):
        return f'&({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = p and q
        evaluated_state.now[self.__str__()] = res
        return res


class Or(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'{self.formula1} | {self.formula2}'

    def __repr__(self):
        return f'|({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = p or q
        evaluated_state.now[self.__str__()] = res
        return res


class Implies(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'{self.formula1} -> {self.formula2}'

    def __repr__(self):
        return f'->({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = (not p) or q
        evaluated_state.now[self.__str__()] = res
        return res


class Iff(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'{self.formula1} <-> {self.formula2}'

    def __repr__(self):
        return f'<->({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)
        res = ((not p) or q) and ((not q) or p)
        evaluated_state.now[self.__str__()] = res
        return res


class Not(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'! {self.formula}'

    def __repr__(self):
        return f'!({repr(self.formula)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]

        p = self.formula.eval(**kwargs)

        res = not p
        evaluated_state.now[self.__str__()] = res
        return res


class EY(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'EY({self.formula})'

    def __repr__(self):
        return f'EY({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for _, summary in evaluated_state.pre.items():
            predecessor_eval = summary[self.formula.__str__()]
            temporal_res = predecessor_eval if temporal_res is None else (temporal_res or predecessor_eval)

        # Continue evaluate the sub-formula inside EY
        self.formula.eval(**kwargs)

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = temporal_res

        return temporal_res


class AY(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'AY({self.formula})'

    def __repr__(self):
        return f'AY({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for _, summary in evaluated_state.pre.items():
            predecessor_eval = summary[self.formula.__str__()]
            temporal_res = predecessor_eval if temporal_res is None else (temporal_res and predecessor_eval)

        # Continue evaluate the sub-formula inside EY
        self.formula.eval(**kwargs)

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = temporal_res

        return temporal_res


class EP(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'EP({self.formula})'

    def __repr__(self):
        return f'EP({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for _, summary in evaluated_state.pre.items():
            predecessor_eval = summary[self.__str__()]
            temporal_res = predecessor_eval if temporal_res is None else (temporal_res or predecessor_eval)

        # Evaluate the sub-formula inside EP
        formula_eval = self.formula.eval(**kwargs)

        # EP('a') considered True if EP('a') was true is at least
        # one predecessor, or we have 'a' in our current state
        current_eval = formula_eval or temporal_res

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class AP(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'AP({self.formula})'

    def __repr__(self):
        return f'AP({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for _, summary in evaluated_state.pre.items():
            predecessor_eval = summary[self.__str__()]
            temporal_res = predecessor_eval if temporal_res is None else (temporal_res and predecessor_eval)

        # Evaluate the sub-formula inside AP
        formula_eval = self.formula.eval(**kwargs)

        # AP('a') considered True if AP('a') was true is all last
        # predecessors, or we have 'a' in our current state
        current_eval = formula_eval or temporal_res

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class EH(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'EH({self.formula})'

    def __repr__(self):
        return f'EH({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for predecessor, summary in evaluated_state.pre.items():

            # Handle the case for first event
            if 'S0' in evaluated_state.pre.keys():
                predecessor_eval = True
            else:
                predecessor_eval = summary[self.__str__()]

            temporal_res = predecessor_eval if temporal_res is None else (temporal_res or predecessor_eval)

        # Evaluate the sub-formula inside EH
        formula_eval = self.formula.eval(**kwargs)

        # EH('a') considered True if EH('a') was true is at least
        # one predecessor, and we have 'a' in our current state
        current_eval = formula_eval and temporal_res

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class AH(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'AH({self.formula})'

    def __repr__(self):
        return f'AH({repr(self.formula)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        for _, summary in evaluated_state.pre.items():

            # Handle the case for first event
            if 'S0' in evaluated_state.pre.keys():
                predecessor_eval = True
            else:
                predecessor_eval = summary[self.__str__()]

            temporal_res = predecessor_eval if temporal_res is None else (temporal_res and predecessor_eval)

        # Evaluate the sub-formula inside AH
        formula_eval = self.formula.eval(**kwargs)

        # AH('a') considered True if AH('a') was true is all last
        # predecessors, and we have 'a' in our current state
        current_eval = formula_eval and temporal_res

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class ES(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'E({self.formula1} S {self.formula2})'

    def __repr__(self):
        return f'ES({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):
        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)

        for predecessor, summary in evaluated_state.pre.items():
            predecessor_eval = summary.get(self.__str__(), False)

            temporal_res = predecessor_eval if temporal_res is None else (temporal_res or predecessor_eval)

        current_eval = q or (p and temporal_res)

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class AS(Formula):
    def __init__(self, formula1, formula2):
        self.formula1 = formula1
        self.formula2 = formula2

    def __str__(self):
        return f'A({self.formula1} S {self.formula2})'

    def __repr__(self):
        return f'AS({repr(self.formula1)}, {repr(self.formula2)})'

    def eval(self, **kwargs):

        # Check if 'state' is in kwargs to avoid KeyError
        if "state" not in kwargs:
            raise ValueError("Missing required 'state' parameter.")

        # Fetch the current evaluated state from kwargs
        evaluated_state: State = kwargs["state"]

        # Init temporal result to None
        temporal_res = None

        p = self.formula1.eval(**kwargs)
        q = self.formula2.eval(**kwargs)

        for predecessor, summary in evaluated_state.pre.items():
            predecessor_eval = summary.get(self.__str__(), False)

            temporal_res = predecessor_eval if temporal_res is None else (temporal_res and predecessor_eval)

        current_eval = q or (p and temporal_res)

        # Update the current evaluated result
        evaluated_state.now[self.__str__()] = current_eval

        return current_eval


class Paren(Formula):
    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return f'({self.formula})'

    def __repr__(self):
        return f'({repr(self.formula)})'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        res = self.formula.eval(**kwargs)
        evaluated_state.now[self.__str__()] = res
        return res


class Constant(Formula):
    def __init__(self, constant):
        self.constant = constant

    def __str__(self):
        return f'{self.constant}'

    def __repr__(self):
        return f'{repr(self.constant)}'

    def eval(self, **kwargs):
        evaluated_state: State = kwargs["state"]
        res = self.constant
        evaluated_state.now[self.__str__()] = res
        return res
