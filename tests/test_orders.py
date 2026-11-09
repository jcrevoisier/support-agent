import pytest

from support_agent.orders import find_order


@pytest.mark.parametrize('value', ['1001', '#1001', ' 1001 ', 'order 1001', 'ORD-1001'])
def test_find_order(value):
    assert find_order(value).product == 'Desk lamp'


@pytest.mark.parametrize('value', ['', 'abc'])
def test_find_order_with_wrong_format(value):
    with pytest.raises(ValueError, match="doesn't look like an order number"):
        find_order(value)


def test_find_order_unknown():
    with pytest.raises(ValueError, match="can't find order 9999"):
        find_order('9999')
