import near


@near.export
def expensive():
    n = int(near.input())
    ret = 0
    sign = 1
    for i in range(n):
        ret += i * sign
        sign *= -1
    near.value_return(str(ret))


def test_expensive():
    for n in [100, 10000, 20000]:
        result, gas_burnt = near.test_method(__file__, "expensive", str(n))
        assert int(result) < 0
        print(f"expensive({n}): {int(result)}, {gas_burnt / 1e12} Tgas")
