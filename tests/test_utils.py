from src.utils import canonical_json_bytes, safe_name, sha256_text


def test_canonical_json_is_key_order_independent():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_safe_name():
    assert safe_name("a/b:c?.mp3") == "a_b_c_.mp3"
    assert sha256_text("x") == sha256_text("x")


def test_safe_hash_json_path_is_deterministic():
    from src.utils import self_hash_json
    data = {"phase2": {"outputs": {"final_json_sha256": None, "x": 1}}, "b": 2}
    assert self_hash_json(data) == self_hash_json(data)
