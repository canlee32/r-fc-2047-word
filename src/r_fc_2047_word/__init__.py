"""r-fc-2047-word: decode RFC 2047 encoded-word email headers."""

from .core import decode_word, decode_line

__all__ = ["decode_word", "decode_line"]
