import ast


def safe_call(expr_text, t):
    expr = ast.parse(expr_text).body[0]
    try:
        val = recurse_call(expr, t)
        return val
    except:
        raise TypeError("Expression not of type "+t+": " + expr_text)
    #if recurse(expr, t):
    #    return eval(expr_text)

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


'''
'''
boolops = {ast.And : (True, bool.__and__), ast.Or : (False, bool.__or__)}
comparisons = {ast.Eq : float.__eq__, ast.NotEq : float.__ne__, ast.Lt : float.__lt__, ast.LtE : float.__le__, ast.Gt : float.__gt__, ast.GtE : float.__ge__}
numops = {ast.Add : float.__add__, ast.Sub : float.__sub__, ast.Mult : float.__mul__, ast.Div : float.__truediv__, ast.Mod : float.__mod__}

def recurse_call(expr, t):
    if isinstance(expr, ast.Expr):
        return recurse_call(expr.value, t)
    elif t == "bool":
        if isinstance(expr, ast.BinOp) and type(expr.op) == ast.Pow:
            return recurse_call(expr.left, "bool") ^ recurse_call(expr.right, "bool")
        elif isinstance(expr, ast.BoolOp):
            flag, oper = boolops[type(expr.op)]
            for val in expr.values:
                flag = oper(flag, recurse_call(val, "bool"))
            return flag
        elif isinstance(expr, ast.UnaryOp) and type(expr.op) == ast.Not:
            return not recurse_call(expr.operand, "bool")
        elif isinstance(expr, ast.Compare):
            flag = True
            comparables = [expr.left] + expr.comparators
            comparables = [recurse_call(val, "num") for val in comparables]
            L = len(expr.ops)
            for i in range(L):
                oper = comparisons[type(expr.ops[i])]
                flag &= oper(float(comparables[i]), float(comparables[i+1]))
            return flag
        elif isinstance(expr, ast.Constant) and isinstance(expr.value, bool):
            return expr.value
        else:
            raise Exception("Bad syntax:", expr)
    elif t == "num":
        if isinstance(expr, ast.BinOp) and type(expr.op) in [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod]:
            oper = numops[type(expr.op)]
            left = recurse_call(expr.left, "num")
            right = recurse_call(expr.right, "num")
            if isinstance(left, int) and isinstance(right, int):
                    fname = oper.__name__
                    newoper = int.__dict__[fname]
                    return newoper(left, right)
            return oper(float(left), float(right))
        elif isinstance(expr, ast.UnaryOp) and type(expr.op) == ast.USub:
            val = recurse_call(expr.operand, "num")
            return -val
        elif isinstance(expr, ast.Constant) and (isinstance(expr.value, int) or isinstance(expr.value, float)):
            return expr.value
        else:
            raise Exception("Bad syntax:", expr)
    else:
        raise Exception("Bad syntax:", expr)
