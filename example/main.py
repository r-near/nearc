import near  # type: ignore


# Store the count in contract storage
@near.export
def new(starting_count=0):
    """Initialize the contract with a starting count."""
    near.storage_write("count", str(starting_count))
    near.value_return("true")
    return True


@near.export
def increment():
    """Increment the counter and return the new value."""
    count = int(near.storage_read("count") or 0)
    count += 1
    near.storage_write("count", str(count))
    near.value_return(str(count))
    return count


@near.export
def decrement():
    """Decrement the counter and return the new value."""
    count = int(near.storage_read("count") or 0)
    count -= 1
    near.storage_write("count", str(count))
    near.value_return(str(count))
    return count


@near.export
def get_count():
    """Get the current count."""
    count = int(near.storage_read("count") or 0)
    near.value_return(str(count))
    return count


@near.export
def reset(value=0):
    """Reset the counter to the given value."""
    near.storage_write("count", str(value))
    near.value_return(str(value))
    return value
