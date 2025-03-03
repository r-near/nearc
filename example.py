import near

@near.export
def hello():
    near.log_utf8("Hello!")
    near.value_return("Hello world")