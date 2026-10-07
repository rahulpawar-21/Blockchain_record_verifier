import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .block import Block, utc_now_iso


class Blockchain:
    def __init__(self, storage_path: str = "data/blockchain.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain: List[Block] = []
        self.load()
        if not self.chain:
            self.chain = [self.create_genesis_block()]
            self.save()

    def create_genesis_block(self) -> Block:
        block = Block(
            index=0,
            timestamp=utc_now_iso(),
            record={"type": "GENESIS", "message": "RecordChain genesis block"},
            previous_hash="0" * 64,
        )
        block.seal()
        return block

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def add_record(self, record: Dict[str, Any]) -> Block:
        block = Block(
            index=len(self.chain),
            timestamp=utc_now_iso(),
            record=record,
            previous_hash=self.latest_block.hash,
        )
        block.seal()
        self.chain.append(block)
        self.save()
        return block

    def validate(self) -> Tuple[bool, List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        for i, block in enumerate(self.chain):
            if block.index != i:
                errors.append({
                    "block_index": block.index,
                    "type": "BLOCK_INDEX_ERROR",
                    "message": "Block index is not in the expected chain position.",
                    "expected": i,
                    "found": block.index,
                })
            calculated = block.calculate_hash()
            if block.hash != calculated:
                errors.append({
                    "block_index": block.index,
                    "type": "HASH_MISMATCH",
                    "message": "Stored hash does not match the block contents.",
                    "stored_hash": block.hash,
                    "calculated_hash": calculated,
                })
            if i == 0:
                if block.previous_hash != "0" * 64:
                    errors.append({
                        "block_index": block.index,
                        "type": "GENESIS_LINK_ERROR",
                        "message": "Genesis block has an invalid previous hash.",
                    })
            else:
                previous = self.chain[i - 1]
                expected_previous_hash = previous.calculate_hash()
                if block.previous_hash != expected_previous_hash:
                    errors.append({
                        "block_index": block.index,
                        "type": "CHAIN_LINK_BROKEN",
                        "message": "Previous hash does not match the previous block hash.",
                        "expected": expected_previous_hash,
                        "found": block.previous_hash,
                    })
        return len(errors) == 0, errors

    def tamper(self, block_index: int, field: str, value: Any) -> Block:
        if block_index <= 0 or block_index >= len(self.chain):
            raise ValueError("Only a non-genesis block can be tampered with in the demo.")
        block = self.chain[block_index]
        if field not in block.record:
            raise ValueError(f"Record field '{field}' does not exist.")
        block.record[field] = value
        # Deliberately DO NOT reseal the block. This simulates an attacker
        # changing historical data without updating its stored hash.
        self.save()
        return block

    def save(self) -> None:
        self.storage_path.write_text(
            json.dumps([block.to_dict() for block in self.chain], indent=2),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.chain = [Block.from_dict(item) for item in raw]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.chain = []

    def to_list(self) -> List[Dict[str, Any]]:
        return [block.to_dict() for block in self.chain]
