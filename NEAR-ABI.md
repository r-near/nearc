Introduction
------------

Interface to NEAR runtime is provided via `near` module.

Everything from https://github.com/near/near-sdk-rs/blob/master/near-sys/src/lib.rs should be available via `near` module. Type signatures differ where required for Python value returns or convenience.

Note: register 0 is used as temporary storage when a NEAR runtime method returns value via register and will be overwritten by such calls


NEAR ABI methods
----------------

```python
# Registers
def read_register(register_id: int) -> bytes
def read_register_as_str(register_id: int) -> str
def register_len(register_id: int) -> int
def write_register(register_id, data: str | bytes) -> None

# Context API
def current_account_id() -> str
def signer_account_id() -> str
def signer_account_pk() -> bytes
def predecessor_account_id() -> str
def input() -> bytes
def input_as_str() -> str
def block_index() -> int
def block_height() -> int
def block_timestamp() -> int
def epoch_height() -> int
def storage_usage() -> int

# Economics API
def account_balance() -> int
def account_locked_balance() -> int
def attached_deposit() -> int
def prepaid_gas() -> int
def used_gas() -> int

# Math API
def random_seed() -> bytes
def sha256(value: bytes) -> bytes
def keccak256(value: bytes) -> bytes
def keccak512(value: bytes) -> bytes
def ripemd160(value: bytes) -> bytes
def ecrecover(hash: bytes, sig: bytes, v: int, malleability_flag: bool) -> bytes | None
def ed25519_verify(sig: bytes, msg: bytes, pub_key: bytes) -> bool

# Miscellaneous API
def value_return(value: str | bytes) -> None
def panic() -> None
def panic_utf8(msg: str) -> None
def log_utf8(msg: str) -> None
def log_utf16(msg: list[int]) -> None
def abort(msg: str, filename: str, line: int, col: int) -> None

# Promises API
def promise_create(account_id: str, function_name: str, arguments: str, amount: int, gas: int) -> int
def promise_then(promise_index: int, account_id: str, function_name: str, arguments: str, amount: int, gas: int) -> int
def promise_and(promise_indices: list[int]) -> int
def promise_batch_create(account_id: str) -> int
def promise_batch_then(promise_index: int, account_id: str) -> int
def promise_batch_action_create_account(promise_index: int) -> None
def promise_batch_action_deploy_contract(promise_index: int, code: bytes) -> None
def promise_batch_action_function_call(promise_index: int, function_name: str, arguments: str, amount: int, gas: int) -> None
def promise_batch_action_function_call_weight(promise_index: int, function_name: str, arguments: str, amount: int, gas: int, weight: int) -> None
def promise_batch_action_transfer(promise_index: int, amount: int) -> None
def promise_batch_action_stake(promise_index: int, amount: int, pub_key: bytes) -> None
def promise_batch_action_add_key_with_full_access(promise_index: int, public_key: bytes, nonce: int) -> None
def promise_batch_action_add_key_with_function_call(promise_index: int, public_key: bytes, nonce: int, allowance: int, receiver_id: str, function_names: str) -> None
def promise_batch_action_delete_key(promise_index: int, public_key: bytes) -> None
def promise_batch_action_delete_account(promise_index: int, beneficiary_id: str) -> None
def promise_yield_create(function_name: str, arguments: str, gas: int, gas_weight: int) -> (int, str)
def promise_yield_resume(data_id: str, payload: str | bytes) -> bool
def promise_results_count() -> int
def promise_result(result_idx: int) -> (int, bytes)
def promise_result_as_str(result_idx: int) -> (int, str)
def promise_return(promise_id: int) -> None

# Storage API
def storage_write(key: str | bytes, value: str | bytes) -> (int, bytes | None)
def storage_read(key: str | bytes) -> (int, bytes | None)
def storage_remove(key: str | bytes) -> (int, bytes | None)
def storage_has_key(key: str | bytes) -> int
def storage_iter_prefix(prefix: str | bytes) -> int
def storage_iter_range(start: str | bytes, end: str | bytes) -> int
def storage_iter_next(iterator_id: int) -> (int, bytes | None, bytes | None)

# Validator API
def validator_stake(account_id: str) -> int
def validator_total_stake() -> int

# Alt BN128 API
def alt_bn128_g1_multiexp(value: bytes) -> bytes
def alt_bn128_g1_sum(value: bytes) -> bytes
def alt_bn128_pairing_check(value: bytes) -> bool
```
