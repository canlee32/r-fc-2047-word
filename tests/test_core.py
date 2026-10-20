"""Unit tests for :mod:`r_fc_2047_word.core`."""

import unittest

from r_fc_2047_word import decode_word, decode_line


class TestDecodeWord(unittest.TestCase):
    def test_q_simple_ascii(self):
        self.assertEqual(decode_word("=?iso-8859-1?Q?hello?="), "hello")

    def test_q_underscore_is_space(self):
        self.assertEqual(decode_word("=?utf-8?Q?hello_world?="), "hello world")

    def test_q_hex_escape(self):
        self.assertEqual(decode_word("=?utf-8?Q?=41=42?="), "AB")

    def test_q_combined_text_and_escapes(self):
        self.assertEqual(decode_word("=?utf-8?Q?Gr=C3=BC=C3=9Fe?="), "Grüße")

    def test_b_simple(self):
        self.assertEqual(decode_word("=?utf-8?B?SGVsbG8=?="), "Hello")

    def test_b_utf8_multibyte(self):
        # "Grüße" base64-encoded as utf-8.
        self.assertEqual(decode_word("=?utf-8?B?R3LDvMOfZQ==?="), "Grüße")

    def test_case_insensitive_encoding(self):
        self.assertEqual(decode_word("=?utf-8?b?SGVsbG8=?="), "Hello")
        self.assertEqual(decode_word("=?utf-8?q?hello?="), "hello")

    def test_non_encoded_word_returned_unchanged(self):
        self.assertEqual(decode_word("plain text"), "plain text")

    def test_unknown_charset_falls_back(self):
        # Bogus charset — we must not raise; latin-1 fallback applies.
        result = decode_word("=?nonsense?Q?hello?=")
        self.assertEqual(result, "hello")

    def test_malformed_q_escape_kept_literal(self):
        # ``=ZZ`` is not a valid hex escape; we keep the '=' literally.
        self.assertEqual(decode_word("=?utf-8?Q?a=ZZb?="), "a=ZZb")

    def test_b_invalid_base64_fallback(self):
        # ``!!!`` is not valid base64; we still return something str-typed.
        result = decode_word("=?utf-8?B?!!!?=")
        self.assertIsInstance(result, str)

    def test_surrounding_whitespace_stripped(self):
        self.assertEqual(decode_word("  =?utf-8?Q?hi?=  "), "hi")


class TestDecodeLine(unittest.TestCase):
    def test_plain_text_unchanged(self):
        self.assertEqual(decode_line("Hello, World"), "Hello, World")

    def test_single_word_in_line(self):
        self.assertEqual(decode_line("Subject: =?utf-8?Q?hello?="), "Subject: hello")

    def test_adjacent_words_whitespace_dropped(self):
        line = "=?utf-8?Q?foo?= =?utf-8?Q?bar?="
        self.assertEqual(decode_line(line), "foobar")

    def test_adjacent_words_tab_separated(self):
        line = "=?utf-8?Q?foo?=\t=?utf-8?Q?bar?="
        self.assertEqual(decode_line(line), "foobar")

    def test_adjacent_words_different_charsets(self):
        # No transcoding attempted; the decoded strings are concatenated
        # verbatim, which is the documented behaviour.
        line = "=?iso-8859-1?Q?caf=E9?= =?utf-8?Q?bar?="
        self.assertEqual(decode_line(line), "cafébar")

    def test_word_with_plain_on_both_sides(self):
        line = "Prefix: =?utf-8?Q?hello?= :Suffix"
        self.assertEqual(decode_line(line), "Prefix: hello :Suffix")

    def test_multiple_words_with_intervening_text(self):
        line = "=?utf-8?Q?alpha?= text =?utf-8?B?QmV0YQ==?="
        self.assertEqual(decode_line(line), "alpha text Beta")

    def test_no_encoded_words(self):
        self.assertEqual(decode_line("Just a subject"), "Just a subject")

    def test_empty_line(self):
        self.assertEqual(decode_line(""), "")


if __name__ == "__main__":
    unittest.main()
