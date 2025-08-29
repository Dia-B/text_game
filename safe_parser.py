import ast


def safe_call(expr_text, t):
    expr = ast.parse(expr_text).body[0]
    if recurse(expr, t):
        return eval(expr_text)
    raise TypeError("Expression not of type "+t+": " + expr_text)

def safe_test(expr_text, t):
    expr = ast.parse(expr_text).body[0]
    return recurse(expr, t)

def recurse(expr, t):
    if isinstance(expr, ast.Expr):
        return recurse(expr.value, t)
    elif t == "bool":
        if isinstance(expr, ast.BinOp) and type(expr.op) == ast.Pow:
            return recurse(expr.left, "bool") and recurse(expr.right, "bool")
        elif isinstance(expr, ast.BoolOp):
            flag = True
            for val in expr.values:
                flag &= recurse(val, "bool")
            return flag
        elif isinstance(expr, ast.UnaryOp) and type(expr.op) == ast.Not:
            return recurse(expr.operand, "bool")
        elif isinstance(expr, ast.Compare):
            flag = True
            for op in expr.ops:
                flag &= (type(op) in [ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE])
            for val in [expr.left] + expr.comparators:
                flag &= recurse(val, "num")
            return flag
        elif isinstance(expr, ast.Constant):
            return isinstance(expr.value, bool)
        else:
            return False
    elif t == "num":
        if isinstance(expr, ast.BinOp) and type(expr.op) in [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod]:
            return recurse(expr.left, "num") and recurse(expr.right, "num")
        elif isinstance(expr, ast.UnaryOp) and type(expr.op) in [ast.UAdd, ast.USub]:
            return recurse(expr.operand, "num")
        elif isinstance(expr, ast.Constant):
            return isinstance(expr.value, int) or isinstance(expr.value, float)
        else:
            return False
    else:
        return False

