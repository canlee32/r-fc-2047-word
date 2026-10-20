"""Decode RFC 2047 ``encoded-word`` fragments found in email headers.

The grammar we recognise is, roughly::

    encoded-word = "=?" charset "?" encoding "?" encoded-text "?="

where *encoding* is ``Q`` (quoted-printable, restricted to the subset
allowed inside encoded-words) or ``B`` (base64).

Design choices
---------------
This module deliberately does *not* re-implement :mod:`email.header`
because that module already folds, unfolds, decodes, and reassembles
headers across newlines.  The narrow job here is: given the text between
a pair of ``=?`` ... ``?=`` delimiters (or a line that contains such
fragments), return the decoded Python string.  We handle adjacent
encoded-words separated by linear-white-space so that the common idiom
``=?utf-8?q?foo?= =?utf-8?q?bar?=`` collapses to ``foobar`` per RFC 2047
§6.2.  When two encoded-words use different charsets we join them
verbatim rather than attempting transcoding; that keeps the library
predictable.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import List, Optional, Tuple

# Matches a single encoded-word including its delimiters.  The text
# portion is permissive (``[^?]+``) because malformed input should be
# returned verbatim by the caller-facing functions, not crash the regex
# engine.
_ENCODED_WORD_RE = re.compile(
    r"=\?([^?]+)\?([BbQq])\?([^?]*)\?="
)

# Inside a ``Q``-encoded word, ``_`` represents 0x20 (space) per RFC 2047
# §4.2.  We substitute it before unquoting ``=XX`` sequences so that the
# quoted-printable decoder only has to cope with the ``=XX`` form.
_Q_WORD_UNDERSCORE_RE = re.compile(r"_")

# A quoted-printable soft-sequence inside an encoded-word.  Only ``=XX``
# hex escapes are legal here (no soft line breaks, unlike full QP bodies).
_QP_HEX_RE = re.compile(r"=([0-9A-Fa-f]{2})")


def _decode_q(encoded_text: str) -> bytes:
    """Decode the ``Q`` encoding subset defined by RFC 2047 §4.2.

    Only literal octets, ``_`` (→ space), and ``=XX`` escapes appear in
    a well-formed Q-encoded word; we do not honour QP soft line breaks
    because the grammar forbids them inside encoded-words.
    """
    text = _Q_WORD_UNDERSCORE_RE.sub(" ", encoded_text)
    out = bytearray()
    pos = 0
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch == "=":
            if pos + 2 < n and text[pos + 1] in "0123456789abcdefABCDEF" and text[pos + 2] in "0123456789abcdefABCDEF":
                out.append(int(text[pos + 1 : pos + 3], 16))
                pos += 3
                continue
            # Malformed escape — keep the literal '=' so callers see the
            # raw input rather than silently dropping bytes.
            out.append(ord("="))
            pos += 1
        else:
            out.append(ord(ch))
            pos += 1
    return bytes(out)


def _decode_b(encoded_text: str) -> bytes:
    """Decode a ``B``-encoded word using the standard-library base64.

    We strip whitespace because some mailers insert it, then tolerate
    :class:`binascii.Error` by returning the original bytes so the caller
    can still surface *something* useful.
    """
    stripped = "".join(encoded_text.split())
    try:
        return base64.b64decode(stripped, validate=False)
    except (binascii.Error, ValueError):
        return stripped.encode("ascii", errors="replace")


def _decode_word_inner(match: str, charset: str, encoding: str, text: str) -> str:
    """Return the decoded *str* for the three capture groups of a word.

    We try the charset named by the word; if Python lacks a codec for it
    we fall back to ``latin-1`` so that bytes survive rather than raising
    :class:`LookupError`.  This mirrors what many MUAs do in practice.
    """
    raw = _decode_b(text) if encoding.upper() == "B" else _decode_q(text)
    try:
        return raw.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("latin-1", errors="replace")


def decode_word(word: str) -> str:
    """Decode a single encoded-word *word* (including ``=?`` ... ``?=``).

    If *word* is not an encoded-word at all, it is returned unchanged so
    that callers can feed a mixture of plain and encoded fragments
    through the same function.
    """
    m = _ENCODED_WORD_RE.fullmatch(word.strip())
    if not m:
        return word
    charset, encoding, text = m.group(1), m.group(2), m.group(3)
    return _decode_word_inner(word, charset, encoding, text)


def _split_tokens(line: str) -> List[Tuple[str, bool]]:
    """Split *line* into ``(fragment, is_encoded_word)`` pairs.

    Linear-white-space between adjacent encoded-words is dropped per
    RFC 2047 §6.2; whitespace elsewhere is preserved.
    """
    tokens: List[Tuple[str, bool]] = []
    pos = 0
    n = len(line)
    while pos < n:
        m = _ENCODED_WORD_RE.match(line, pos)
        if m:
            tokens.append((m.group(0), True))
            pos = m.end()
            # Eat linear-white-space between two encoded-words.
            if pos < n and line[pos] in " \t":
                peek = pos
                while peek < n and line[peek] in " \t":
                    peek += 1
                if peek < n and line[peek:peek + 2] == "=?":
                    pos = peek
            continue
        # Find the next encoded-word start so plain text includes up to it.
        next_start = line.find("=?", pos)
        if next_start == -1:
            tokens.append((line[pos:], False))
            break
        tokens.append((line[pos:next_start], False))
        pos = next_start
    return tokens


def decode_line(line: str) -> str:
    """Decode every encoded-word in *line*, leaving plain text untouched.

    Adjacent encoded-words separated only by linear-white-space are
    concatenated without a space, per RFC 2047 §6.2.
    """
    parts: List[str] = []
    for fragment, is_word in _split_tokens(line):
        if is_word:
            m = _ENCODED_WORD_RE.fullmatch(fragment)
            assert m is not None  # _split_tokens guarantees this
            parts.append(_decode_word_inner(m.group(0), m.group(1), m.group(2), m.group(3)))
        else:
            parts.append(fragment)
    return "".join(parts)
