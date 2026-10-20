# r-fc-2047-word

Decodes RFC 2047 `encoded-word` fragments in email headers (the `=?charset?encoding?text?=` syntax), returning Python strings.

## Usage

```python
from r_fc_2047_word import decode_word, decode_line

# Decode a single encoded-word, including its =? ... ?= delimiters.
assert decode_word("=?utf-8?Q?Gr=C3=BC=C3=9Fe?=") == "Grüße"
assert decode_word("=?utf-8?B?R3LDvMOfZQ==?=") == "Grüße"

# Decode every encoded-word in a line, leaving plain text untouched.
assert decode_line("Subject: =?utf-8?Q?hello?=") == "Subject: hello"
```

## Why

The standard library's `email.header` module decodes entire headers, folding and reassembling them across line breaks. That's the right tool when you want full header parsing. This library exists for the narrower job: you already have a fragment of a header (perhaps extracted by some other parser) and you want the decoded text for just the `encoded-word` portions, without the surrounding machinery.

The trade-off is that this library does not unfold headers or handle MIME-word splitting across physical line boundaries; it expects logical, unfolded input. If your input contains raw `\r\n` line continuations, unfold them first.

## Edge cases

Adjacent encoded-words separated by linear-white-space (` ` or `\t`) are concatenated without a space, per RFC 2047 §6.2. Two encoded-words using different charsets are joined verbatim; no transcoding is attempted. Unknown charsets fall back to latin-1 so bytes survive rather than raising `LookupError`.
