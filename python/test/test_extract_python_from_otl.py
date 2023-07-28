import re
import extract_python_from_otl as epfo


def test_do_something():
    result = epfo.get_hash(1)
    assert result is not None
    assert isinstance(result, str)
    regex = re.compile(r"^[a-f0-9]+$")
    assert regex.match(result)
