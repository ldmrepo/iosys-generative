"""Encoding utilities for EUC-KR to UTF-8 conversion."""

from pathlib import Path


def decode_euckr(data: bytes) -> str:
    """
    Decode EUC-KR (ksc5601) encoded bytes to UTF-8 string.

    Tries multiple encodings in order of preference:
    1. euc-kr (most common)
    2. cp949 (Windows Korean, superset of EUC-KR)
    3. utf-8 (in case file is already UTF-8)

    Args:
        data: Raw bytes to decode

    Returns:
        Decoded UTF-8 string

    Raises:
        UnicodeDecodeError: If all decodings fail
    """
    encodings = ["euc-kr", "cp949", "utf-8", "utf-8-sig"]

    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue

    # Last resort: decode with errors='replace'
    return data.decode("euc-kr", errors="replace")


def read_file_with_encoding(file_path: Path) -> str:
    """
    Read a file with automatic encoding detection.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as UTF-8 string
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    return decode_euckr(raw_data)


def convert_file_to_utf8(input_path: Path, output_path: Path) -> None:
    """
    Convert a file from EUC-KR to UTF-8.

    Also updates the XML declaration encoding if present.

    Args:
        input_path: Path to the source file
        output_path: Path to write the converted file
    """
    content = read_file_with_encoding(input_path)

    # Update XML encoding declaration if present
    content = content.replace('encoding="ksc5601"', 'encoding="utf-8"')
    content = content.replace("encoding='ksc5601'", "encoding='utf-8'")
    content = content.replace('encoding="euc-kr"', 'encoding="utf-8"')
    content = content.replace("encoding='euc-kr'", "encoding='utf-8'")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
