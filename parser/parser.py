# parser/parser.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# PCTL formula parser using PLY (Python Lex-Yacc) for tokenizing and parsing
# past-time temporal logic expressions into abstract syntax trees.

from typing import Optional

import ply.lex as lex
import ply.yacc as yacc

from parser.ast import (
    EH,
    Proposition,
    And,
    Or,
    Implies,
    Not,
    Iff,
    AS,
    ES,
    AP,
    EP,
    AH,
    AY,
    EY,
    Paren,
    Constant,
    error,
    Formula,
)

errors = False

# Token definitions
tokens = (
    "A",
    "E",
    "S",
    "AND",
    "OR",
    "IMPLIES",
    "IFF",
    "NOT",
    "EP",
    "AP",
    "EY",
    "AY",
    "EH",
    "AH",
    "LPAREN",
    "RPAREN",
    "PROPOSITION",
    "TRUE",
    "FALSE",
)

# Logical operators
t_AND = r"\&"
t_OR = r"\|"
t_NOT = r"\!"
t_IMPLIES = r"->"
t_IFF = r"<->"

# Temporal operators
t_A = r"A"
t_E = r"E"
t_S = r"S"
t_AP = r"AP"
t_EP = r"EP"
t_AY = r"AY"
t_EY = r"EY"
t_AH = r"AH"
t_EH = r"EH"

# Constants
t_TRUE = r"TRUE"
t_FALSE = r"FALSE"

# Parentheses
t_LPAREN = r"\("
t_RPAREN = r"\)"

# Reserved words
RESERVED = {
    "A": "A",
    "E": "E",
    "S": "S",
    "EP": "EP",
    "AP": "AP",
    "EH": "EH",
    "AH": "AH",
    "EY": "EY",
    "AY": "AY",
    "TRUE": "TRUE",
    "FALSE": "FALSE",
}


def t_PROPOSITION(t):
    r"[a-zA-Z_][a-zA-Z0-9_\'\.]*"
    t.type = RESERVED.get(t.value, "PROPOSITION")
    return t


t_ignore = " \t \n \r"


def t_newline(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


def _find_column(input_text: str, token) -> int:
    """Find column position of token for error reporting."""
    i = token.lexpos
    while i > 0:
        if input_text[i] == "\n":
            break
        i -= 1
    return (token.lexpos - i) + 1


def t_error(t):
    """Handle lexer errors."""
    global errors
    errors = True
    lexpos = _find_column(t.lexer.lexdata, t)
    print(
        f"lexer error, illegal character '{t.value[0]}', line '{t.lineno}', pos '{lexpos}'"
    )
    t.lexer.skip(1)


# Grammar rules
def p_formula_proposition(p):
    """formula : PROPOSITION"""
    p[0] = Proposition(p[1])


def p_formula_and(p):
    """formula : formula AND formula"""
    p[0] = And(p[1], p[3])


def p_formula_or(p):
    """formula : formula OR formula"""
    p[0] = Or(p[1], p[3])


def p_formula_implies(p):
    """formula : formula IMPLIES formula"""
    p[0] = Implies(p[1], p[3])


def p_formula_iff(p):
    """formula : formula IFF formula"""
    p[0] = Iff(p[1], p[3])


def p_formula_not(p):
    """formula : NOT formula"""
    p[0] = Not(p[2])


def p_formula_as(p):
    """formula : A LPAREN formula S formula RPAREN"""
    p[0] = AS(p[3], p[5])


def p_formula_es(p):
    """formula : E LPAREN formula S formula RPAREN"""
    p[0] = ES(p[3], p[5])


def p_formula_ap(p):
    """formula : AP formula"""
    p[0] = AP(p[2])


def p_formula_ep(p):
    """formula : EP formula"""
    p[0] = EP(p[2])


def p_formula_ah(p):
    """formula : AH formula"""
    p[0] = AH(p[2])


def p_formula_eh(p):
    """formula : EH formula"""
    p[0] = EH(p[2])


def p_formula_ay(p):
    """formula : AY formula"""
    p[0] = AY(p[2])


def p_formula_ey(p):
    """formula : EY formula"""
    p[0] = EY(p[2])


def p_formula_paren(p):
    """formula : LPAREN formula RPAREN"""
    p[0] = Paren(p[2])


def p_formula_true(p):
    """formula : TRUE"""
    p[0] = Constant(True)


def p_formula_false(p):
    """formula : FALSE"""
    p[0] = Constant(False)


# Operator precedence
precedence = (
    ("right", "A", "E"),
    ("left", "S"),
    ("left", "IFF"),
    ("left", "IMPLIES"),
    ("left", "OR"),
    ("left", "AND"),
    ("right", "NOT", "EH", "AH", "EY", "AY", "EP", "AP"),
)


def p_error(p):
    """Handle parser errors."""
    global errors
    errors = True
    if p:
        print(f"Syntax error at '{p.value}' in line '{p.lineno}'")
    else:
        print("Syntax error at EOF")


# Initialize lexer and parser
lex.lex(debug=False)
parser = yacc.yacc(debug=False)


def parse(formula: str) -> Optional[Formula]:
    """Parse PCTL formula string into AST."""
    global errors
    errors = False
    tree = parser.parse(formula)

    if errors:
        error(f"Syntax error! (please check your formula: '{formula}')")
        return None
    else:
        return tree
