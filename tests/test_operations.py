from app.operations import *; import pytest
def test_all():
    assert sqrt(9)==3
    assert factorial(5)==120
    assert factorial(4)==24
    assert power(2,3)==8
    assert pytest.approx(ln(2.71828),rel=1e-3)==1
#checking4