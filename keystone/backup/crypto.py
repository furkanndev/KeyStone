"""Streaming authenticated encryption for backup archives.

Format (all integers big-endian):
    MAGIC (8) | salt (16) | nonce_prefix (8) | { len (4) | AES-256-GCM(chunk) }...

* Key = scrypt(password, salt, n=2**15, r=8, p=1) -> 32 bytes.
* Chunk i is sealed with nonce = nonce_prefix || i (4 bytes) and AAD
  b"more" / b"last", so reordering, dropping or truncating chunks fails.
"""
from __future__ import annotations

import os
import struct
from typing import BinaryIO

MAGIC = b"KSBAKE01"
CHUNK = 1 << 20


class CryptoUnavailable(RuntimeError):
    pass


class BadPassword(ValueError):
    pass


def _aes(key: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover
        raise CryptoUnavailable("The 'cryptography' package is required for encrypted backups") from exc
    return AESGCM(key)


def derive(password: str, salt: bytes) -> bytes:
    import hashlib
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2 ** 15, r=8, p=1,
                          maxmem=64 * 1024 * 1024, dklen=32)


def is_encrypted(path: str) -> bool:
    with open(path, "rb") as fh:
        return fh.read(len(MAGIC)) == MAGIC


def encrypt_stream(src: BinaryIO, dst: BinaryIO, password: str) -> None:
    salt, prefix = os.urandom(16), os.urandom(8)
    aes = _aes(derive(password, salt))
    dst.write(MAGIC + salt + prefix)
    i = 0
    cur = src.read(CHUNK)
    while True:
        nxt = src.read(CHUNK)
        last = not nxt
        ct = aes.encrypt(prefix + struct.pack(">I", i), cur, b"last" if last else b"more")
        dst.write(struct.pack(">I", len(ct)) + ct)
        if last:
            return
        cur, i = nxt, i + 1


def decrypt_stream(src: BinaryIO, dst: BinaryIO, password: str) -> None:
    from cryptography.exceptions import InvalidTag

    if src.read(len(MAGIC)) != MAGIC:
        raise ValueError("not an encrypted KeyStone backup")
    salt, prefix = src.read(16), src.read(8)
    aes = _aes(derive(password, salt))
    i = 0
    while True:
        hdr = src.read(4)
        if len(hdr) < 4:
            raise ValueError("backup is truncated")
        (n,) = struct.unpack(">I", hdr)
        ct = src.read(n)
        nonce = prefix + struct.pack(">I", i)
        try:
            pt = aes.decrypt(nonce, ct, b"more")
            last = False
        except InvalidTag:
            try:
                pt = aes.decrypt(nonce, ct, b"last")
                last = True
            except InvalidTag:
                if i == 0:
                    raise BadPassword("wrong password") from None
                raise ValueError("backup is corrupted") from None
        dst.write(pt)
        if last:
            if src.read(1):
                raise ValueError("unexpected data after final chunk")
            return
        i += 1
