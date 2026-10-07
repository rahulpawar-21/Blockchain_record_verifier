import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class Block:
    index: int
    timestamp: str
    record: Dict[str, Any]
    previous_hash: str
    hash: str = ""

    def calculate_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "record": self.record,
            "previous_hash": self.previous_hash,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def seal(self) -> None:
        self.hash = self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            record=data["record"],
            previous_hash=data["previous_hash"],
            hash=data.get("hash", ""),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
