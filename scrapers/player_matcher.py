"""Player matching utilities for ESPN ID mapping."""

# Cyrillic to ASCII character mappings
CYRILLIC_TO_ASCII = {
    '\u0435': 'e',  # Cyrillic е -> e
    '\u0430': 'a',  # Cyrillic а -> a
    '\u043e': 'o',  # Cyrillic о -> o
    '\u0440': 'p',  # Cyrillic р -> p (looks like p)
    '\u0441': 'c',  # Cyrillic с -> c
    '\u0443': 'y',  # Cyrillic у -> y
    '\u0445': 'x',  # Cyrillic х -> x
}


def normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    Args:
        name: Player name to normalize

    Returns:
        Lowercase name with Cyrillic chars replaced and whitespace stripped
    """
    # Lowercase
    result = name.lower()

    # Replace Cyrillic lookalikes with ASCII
    for cyrillic, ascii_char in CYRILLIC_TO_ASCII.items():
        result = result.replace(cyrillic, ascii_char)

    # Strip whitespace
    return result.strip()
