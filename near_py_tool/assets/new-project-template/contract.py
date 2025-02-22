import json

import base58
import near


@near.export
def hello_world():
    input_bytes = near.input()
    base58_input = base58.b58encode(input_bytes).decode("ascii")
    near.log_utf8(f"hello_world(): input(): {input_bytes.decode('ascii')}; b58(input(0)): {base58_input}")
    near.value_return(json.dumps({"input_length": len(input_bytes), "base58_input": base58_input}))


@near.export
def echo():
    input_bytes = near.input()
    base58_input = base58.b58encode(input_bytes).decode("ascii")
    near.log_utf8(f"hello_world(): input(): {input_bytes.decode('ascii')}; b58(input(0)): {base58_input}")
    near.value_return(json.dumps({"input_length": len(input_bytes), "base58_input": base58_input}))
