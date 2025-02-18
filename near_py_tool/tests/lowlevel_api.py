import near


@near.export
def lowlevel_storage_write():
    data = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    near.storage_write(data, data)


@near.export
def lowlevel_storage_write_many():
    data = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)
    near.storage_write(data, data)


def test_lowlevel_storage_write():
    result, gas_burnt = near.test_method(__file__, "lowlevel_storage_write", {})


def test_lowlevel_storage_write_many():
    result, gas_burnt = near.test_method(__file__, "lowlevel_storage_write_many", {})
