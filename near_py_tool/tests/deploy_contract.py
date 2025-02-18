import near
import math


@near.export
def deploy_contract():
    promise_id = near.promise_batch_create("a.caller.test.near")
    near.promise_batch_action_create_account(promise_id)
    near.promise_batch_action_transfer(promise_id, 10000000000000000000000000)
    near.promise_batch_action_deploy_contract(
        promise_id,
        near.include_contract_wasm("promise_api.py"),
    )
    near.promise_batch_action_FunctionCall(
        promise_id, "cross_contract_callee", "abc", 0, 2 * math.pow(10, 13)
    )
    near.promise_return(promise_id)


def test_deploy_contract(request):
    wasm_path = near.build_contract(__file__.replace("deploy_contract.py", "promise_api.py"))
    with open(wasm_path, 'rb') as f:
      wasm_data = f.read()
    with open(__file__, 'r') as f:
      contract_text = f.read()
    processed_contract_path = __file__.replace("deploy_contract.py", "deploy_contract_temp.py")
    with open(processed_contract_path, 'w') as f:
      f.write(contract_text.replace('near.include_contract_wasm(' + '"promise_api.py")', repr(wasm_data)))      
    result, gas_burnt = near.test_method(processed_contract_path, "deploy_contract", {})
    assert isinstance(result["current_account_id"], str)
    assert isinstance(result["signer_account_id"], str)
    assert isinstance(result["predecessor_account_id"], str)
    assert isinstance(result["input"], dict)
