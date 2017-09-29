from typing import List

from flask import Flask

from flask_typed_mounter import TypedMounter


app = Flask(__name__)
tm = TypedMounter(app)


@tm.attach_endpoint('/mul', methods=['POST'], auto_document=True)
def multiplier(val1: int, names:List[str], val2: int = 5):
    """
    A function which retrieves a value from the given *list* with a given **index**
    and returns it a given number of times 😲

    :param names: list of names
    :param val1: a number
    :param val2: another number, defaults to 5
    :return: the product of the two values
    """
    if val2 ==7:
        print(23 / 0)
    return names[val1] * val2
