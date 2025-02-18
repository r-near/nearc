import near


@near.export
def empty():
    pass


def test_empty():
    result, gas_burnt = near.test_method(__file__, "empty", {})
