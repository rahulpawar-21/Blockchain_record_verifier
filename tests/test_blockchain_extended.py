from blockchain.blockchain import Blockchain


def make_chain(tmp_path):
    return Blockchain(str(tmp_path / "chain.json"))


def test_multiple_records_and_links(tmp_path):
    chain = make_chain(tmp_path)
    b1 = chain.add_record({"certificate_id": "CERT1", "marks": 85})
    b2 = chain.add_record({"certificate_id": "CERT2", "marks": 92})
    b3 = chain.add_record({"certificate_id": "CERT3", "marks": 78})
    assert [b.index for b in chain.chain] == [0, 1, 2, 3]
    assert b2.previous_hash == b1.hash
    assert b3.previous_hash == b2.hash
    assert chain.validate() == (True, [])


def test_legitimate_correction_is_a_new_block(tmp_path):
    chain = make_chain(tmp_path)
    original = chain.add_record({"type": "MARKS_RECORD", "certificate_id": "CERT1", "marks": 85})
    correction = chain.add_record({"type": "MARKS_CORRECTION", "certificate_id": "CERT1", "previous_marks": 85, "marks": 90})
    assert original.record["marks"] == 85
    assert correction.record["marks"] == 90
    assert correction.previous_hash == original.hash
    assert chain.validate() == (True, [])


def test_any_historical_data_change_changes_calculated_hash(tmp_path):
    chain = make_chain(tmp_path)
    block = chain.add_record({"certificate_id": "CERT1", "marks": 85})
    original_hash = block.hash
    block.record["marks"] = 90
    assert block.calculate_hash() != original_hash


def test_tamper_breaks_both_hash_and_chain_link(tmp_path):
    chain = make_chain(tmp_path)
    chain.add_record({"certificate_id": "CERT1", "marks": 85})
    chain.add_record({"certificate_id": "CERT2", "marks": 92})
    chain.tamper(1, "marks", 99)
    valid, errors = chain.validate()
    assert not valid
    types = {e["type"] for e in errors}
    assert "HASH_MISMATCH" in types
    assert "CHAIN_LINK_BROKEN" in types


def test_genesis_cannot_be_tampered_with_using_demo_api(tmp_path):
    chain = make_chain(tmp_path)
    try:
        chain.tamper(0, "message", "changed")
    except ValueError as exc:
        assert "non-genesis" in str(exc)
    else:
        raise AssertionError("Genesis tampering should be rejected")


def test_corrupt_block_index_is_detected(tmp_path):
    chain = make_chain(tmp_path)
    chain.add_record({"certificate_id": "CERT1", "marks": 85})
    chain.chain[1].index = 7
    valid, errors = chain.validate()
    assert not valid
    assert any(e["type"] == "BLOCK_INDEX_ERROR" for e in errors)
