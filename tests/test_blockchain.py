from blockchain.block import Block
from blockchain.blockchain import Blockchain


def test_hash_changes_when_data_changes(tmp_path):
    chain = Blockchain(str(tmp_path / "chain.json"))
    block = chain.add_record({"certificate_id": "CERT1", "marks": 85})
    original = block.hash
    block.record["marks"] = 90
    assert block.calculate_hash() != original


def test_tampering_breaks_chain(tmp_path):
    chain = Blockchain(str(tmp_path / "chain.json"))
    chain.add_record({"certificate_id": "CERT1", "marks": 85})
    chain.add_record({"certificate_id": "CERT2", "marks": 92})
    valid, errors = chain.validate()
    assert valid
    assert errors == []

    chain.tamper(1, "marks", 99)
    valid, errors = chain.validate()
    assert not valid
    assert any(e["type"] == "HASH_MISMATCH" for e in errors)


def test_genesis_is_valid(tmp_path):
    chain = Blockchain(str(tmp_path / "chain.json"))
    assert chain.validate()[0]
    assert chain.chain[0].record["type"] == "GENESIS"
