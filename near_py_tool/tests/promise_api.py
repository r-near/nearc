import near
import math
import json

# Functions consumed by the promise api tests


@near.export
def just_panic():
    raise RuntimeError("it just panic")


@near.export
def write_some_state():
    # Attempt to write something in state. If this one is successfully executed and not revoked, these should be in state
    near.storage_write("aaa", "bbb")
    near.storage_write("ccc", "ddd")
    near.storage_write("eee", "fff")


def calling_data():
    return {
        "current_account_id": near.current_account_id(),
        "signer_account_id": near.signer_account_id(),
        "predecessor_account_id": near.predecessor_account_id(),
        "input": near.input(),
    }


@near.export
def cross_contract_callee():
    near.value_return(json.dumps(calling_data()))


@near.export
def cross_contract_call_gas():
    near.value_return(str(near.prepaid_gas()))


@near.export
def cross_contract_callback():
    result = calling_data()
    result["promise_results"] = [near.promise_result(i) for i in range(near.promise_results_count())]
    near.value_return(json.dumps(result))


@near.export
def test_promise_create():
    near.promise_create(
        "callee-contract.test.near",
        "cross_contract_callee",
        "abc",
        0,
        2 * math.pow(10, 13),
    )


@near.export
def test_promise_create_gas_overflow():
    near.promise_create(
        "callee-contract.test.near", "cross_contract_callee", "abc", 0, math.pow(2, 64)
    )


@near.export
def test_promise_then():
    promise_id = near.promise_create(
        "callee-contract.test.near",
        "cross_contract_callee",
        "abc",
        0,
        2 * math.pow(10, 13),
    )
    near.promise_then(
        promise_id,
        "caller-contract.test.near",
        "cross_contract_callback",
        "def",
        0,
        2 * math.pow(10, 13),
    )


@near.export
def test_promise_and():
    promise_id = near.promise_create(
        "callee-contract.test.near",
        "cross_contract_callee",
        "abc",
        0,
        2 * math.pow(10, 13),
    )
    promise2_id = near.promise_create(
        "callee-contract.test.near",
        "cross_contract_callee",
        "def",
        0,
        2 * math.pow(10, 13),
    )
    promise_id_and = near.promise_and([promise_id, promise2_id])
    near.promise_then(
        promise_id_and,
        "caller-contract.test.near",
        "cross_contract_callback",
        "ghi",
        0,
        3 * math.pow(10, 13),
    )
