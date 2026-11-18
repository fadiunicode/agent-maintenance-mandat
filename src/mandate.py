"""Signature et vérification du mandat (HMAC-SHA256).

L'opérateur signe le mandat ; à bord, le vérificateur refuse un mandat dont la
signature ne correspond pas (mandat modifié après signature).
Note : HMAC suffit pour ce prototype ; une signature asymétrique (Ed25519) ou un
jeton de capacité (Biscuit) serait plus adaptée en conditions réelles.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY = "cle-demo-a-remplacer"


def _canonical(mandate: dict) -> bytes:
    body = {k: v for k, v in mandate.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign(mandate: dict, key: str | None = None) -> dict:
    key = (key or os.getenv("MANDATE_KEY", DEFAULT_KEY)).encode()
    signed = dict(mandate)
    signed["signature"] = hmac.new(key, _canonical(mandate), hashlib.sha256).hexdigest()
    return signed


def is_valid(mandate: dict, key: str | None = None) -> bool:
    if "signature" not in mandate:
        return False
    expected = sign(mandate, key)["signature"]
    return hmac.compare_digest(expected, mandate["signature"])


def load_signed(path: Path = ROOT / "mandate.signed.json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raw = json.loads((ROOT / "mandate.json").read_text(encoding="utf-8"))
    out = ROOT / "mandate.signed.json"
    out.write_text(json.dumps(sign(raw), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Mandat signé : {out}")
