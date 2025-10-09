import math
def sqrt(x: float) -> float:
    x = float(x)
    if x < 0: raise ValueError("sqrt is undefined for negative numbers")
    return math.sqrt(x)
def factorial(n: int) -> int:
    if isinstance(n, float) and not n.is_integer(): raise ValueError("factorial is for non-negative integers only")
    n = int(n)
    if n < 0: raise ValueError("factorial is for non-negative integers only")
    return math.factorial(n)
def ln(x: float) -> float:
    x = float(x)
    if x <= 0: raise ValueError("ln is defined for positive numbers only")
    return math.log(x)
def power(x: float, b: float) -> float: return float(x)**float(b)
