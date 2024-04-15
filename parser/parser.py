import ply.lex as lex
import ply.yacc as yacc

from parser.ast import *

errors = False

#################
###   Lexer   ###
#################

tokens = (
    'A',
    'E',
    'S',
    'AND',
    'OR',
    'IMPLIES',
    'IFF',
    'NOT',
    'EP',
    'AP',
    'EY',
    'AY',
    'EH',
    'AH',
    'LPAREN',
    'RPAREN',
    'PROPOSITION',
    'TRUE',
    'FALSE'
)

# Basic logical operators
t_AND = r'\&'
t_OR = r'\|'
t_NOT = r'\!'
t_IMPLIES = r'->'
t_IFF = r'<->'

# Temporal operators
t_A = r'A'
t_E = r'E'
t_S = r'S'
t_AP = r'AP'
t_EP = r'EP'
t_AY = r'AY'
t_EY = r'EY'
t_AH = r'AH'
t_EH = r'EH'

# Add rules for TRUE and FALSE
t_TRUE = r'TRUE'
t_FALSE = r'FALSE'

# Parentheses
t_LPAREN = r'\('
t_RPAREN = r'\)'

RESERVED = {
    "A": 'A',
    "E": 'E',
    "S": 'S',
    "EP": 'EP',
    "AP": 'AP',
    "EH": 'EH',
    "AH": 'AH',
    "EY": 'EY',
    "AY": 'AY',
    "TRUE": 'TRUE',
    "FALSE": 'FALSE'
}


def t_PROPOSITION(t):
    r'[a-zA-Z_][a-zA-Z0-9_\'\.]*'
    t.type = RESERVED.get(t.value, "PROPOSITION")
    return t


t_ignore = " \t \n \r"


def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")


def find_column(input, token):
    i = token.lexpos
    while i > 0:
        if input[i] == '\n':
            break
        i -= 1
    column = (token.lexpos - i) + 1
    return column


def t_error(t):
    global errors
    errors = True
    lexpos = find_column(t.lexer.lexdata, t)
    print(f"lexer error, illegal character '{t.value[0]}', line '{t.lineno}', pos '{lexpos}'")
    t.lexer.skip(1)


################
###  Parser  ###
################

def p_formula_0(p):
    """formula : PROPOSITION"""
    p[0] = Proposition(p[1])


def p_formula_1(p):
    """formula : formula AND formula"""
    p[0] = And(p[1], p[3])


def p_formula_2(p):
    """formula : formula OR formula"""
    p[0] = Or(p[1], p[3])


def p_formula_3(p):
    """formula : formula IMPLIES formula"""
    p[0] = Implies(p[1], p[3])


def p_formula_4(p):
    """formula : formula IFF formula"""
    p[0] = Iff(p[1], p[3])


def p_formula_5(p):
    """formula : NOT formula"""
    p[0] = Not(p[2])


def p_formula_6(p):
    """formula : A LPAREN formula S formula RPAREN"""
    p[0] = AS(p[3], p[5])


def p_formula_7(p):
    """formula : E LPAREN formula S formula RPAREN"""
    p[0] = ES(p[3], p[5])


def p_formula_8(p):
    """formula : AP formula"""
    p[0] = AP(p[2])


def p_formula_9(p):
    """formula : EP formula"""
    p[0] = EP(p[2])


def p_formula_10(p):
    """formula : AH formula"""
    p[0] = EP(p[2])


def p_formula_11(p):
    """formula : EH formula"""
    p[0] = EH(p[2])


def p_formula_12(p):
    """formula : AY formula"""
    p[0] = AY(p[2])


def p_formula_14(p):
    """formula : EY formula"""
    p[0] = EY(p[2])


def p_formula_15(p):
    """formula : LPAREN formula RPAREN"""
    p[0] = Paren(p[2])


def p_formula_true(p):
    "formula : TRUE"
    p[0] = Constant(True)


def p_formula_false(p):
    "formula : FALSE"
    p[0] = Constant(False)


precedence = (
    ('right', 'A', 'E'),
    ('left', 'S'),
    ('left', 'IFF'),
    ('left', 'IMPLIES'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT')
)


def p_error(p):
    global errors
    errors = True
    if p:
        print(f"Syntax error at '{p.value}' in line '{p.lineno}'")
    else:
        print("Syntax error at EOF")


lex.lex(debug=False)
parser = yacc.yacc(debug=False)


def parse(formula: str) -> Formula | None:
    global errors
    errors = False
    tree = parser.parse(formula)
    if errors:
        error(f"Syntax error! (please check your formula: '{formula}')")
    else:
        return tree
