import base64
import hashlib
import struct
import math
from typing import Optional

try:
    import face_recognition  # optional dependency; may not be installed in all envs
    FACE_LIB_AVAILABLE = True
except Exception:
    FACE_LIB_AVAILABLE = False


def embed_from_image_base64(b64: str) -> bytes:
    """Return a binary embedding for the given base64 image.

    If the optional `face_recognition` library is available this returns a
    packed float32 vector (128 floats) as bytes. Otherwise falls back to a
    deterministic SHA-256 digest of the raw image bytes (legacy behavior).
    """
    try:
        raw = base64.b64decode(b64)
    except Exception:
        raw = b""

    if FACE_LIB_AVAILABLE and raw:
        try:
            # face_recognition can load from a file-like object
            from io import BytesIO

            img = face_recognition.load_image_file(BytesIO(raw))
            encs = face_recognition.face_encodings(img)
            if encs:
                vec = encs[0]
                # pack as float32 sequence
                return struct.pack("%sf" % len(vec), *[float(x) for x in vec])
        except Exception:
            # fall through to sha256 fallback
            pass

    # fallback: deterministic sha256 of image bytes
    return hashlib.sha256(raw).digest()


def _unpack_floats(b: bytes) -> Optional[list]:
    if not b or len(b) % 4 != 0:
        return None
    count = len(b) // 4
    try:
        return list(struct.unpack("%sf" % count, b))
    except Exception:
        return None


def similarity(a: bytes, b: bytes) -> float:
    """Compute similarity between two embeddings.

    If both embeddings unpack to float arrays, use cosine similarity.
    Otherwise fall back to the previous byte-wise normalized L1 similarity.
    Returns value in [0.0, 1.0].
    """
    if not a or not b or len(a) != len(b):
        return 0.0

    fa = _unpack_floats(a)
    fb = _unpack_floats(b)
    if fa is not None and fb is not None:
        # cosine similarity
        dot = sum(x * y for x, y in zip(fa, fb))
        na = math.sqrt(sum(x * x for x in fa))
        nb = math.sqrt(sum(y * y for y in fb))
        if na == 0 or nb == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (na * nb)))

    # fallback: normalized 1 - L1/Max
    s = 0
    for x, y in zip(a, b):
        s += abs(x - y)
    maxd = 255 * len(a)
    return max(0.0, 1.0 - (s / maxd))


def face_lib_available() -> bool:
    return FACE_LIB_AVAILABLE
