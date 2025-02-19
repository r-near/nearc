import near
import json


@near.export
def deploy_contract():
    promise_id = near.promise_batch_create("$promise_api_contract_account_id")
    near.promise_batch_action_create_account(promise_id)
    near.promise_batch_action_transfer(promise_id, 4500000000000000000000000)
    near.promise_batch_action_deploy_contract(
        promise_id,
        b"$promise_api.wasm",
    )
    near.promise_batch_action_function_call(
        promise_id, "cross_contract_callee", "abc", 0, 20000000000000
    )
    near.promise_return(promise_id)


def test_deploy_contract():
    near.test_add_extra_balance() # this ensures test account balance is enough for this + deployed contract storage (~1400KB or ~14 NEAR)
    test_account_id = near.test_account_id()
    promise_api_contract_account_id = f"{id(object())}.{test_account_id}"
    wasm_path = near.build_contract(
        __file__.replace("deploy_contract.py", "promise_api.py")
    )
    with open(wasm_path, "rb") as f:
        wasm_data = f.read()
    with open(__file__, "r") as f:
        contract_text = f.read()
    processed_contract_path = __file__.replace(
        "deploy_contract.py", "deploy_contract_temp.py"
    )
    with open(processed_contract_path, "w") as f:
        f.write(
            contract_text.replace('b"$' + 'promise_api.wasm"', repr(wasm_data)).replace(
                "$" + "promise_api_contract_account_id", promise_api_contract_account_id
            )
        )
    result, gas_burnt = near.test_method(
        processed_contract_path, "deploy_contract", {}, attached_deposit=0
    )
    result_json = json.loads(result)
    assert result_json["current_account_id"] == promise_api_contract_account_id
    assert result_json["signer_account_id"] == test_account_id
    assert result_json["predecessor_account_id"] == test_account_id
    assert result_json["input"] == "abc"
