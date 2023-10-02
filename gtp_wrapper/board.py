import re
from dataclasses import dataclass
from typing import NamedTuple

def gtp_ord(c: str) -> int:
    """Convert a letter to its GTP format ordinal.
    
    >>> gtp_ord("A")
    0
    >>> gtp_ord("Z")
    24

    """
    assert ord('A') <= ord(c) <= ord('Z') and c != 'I'
    return ord(c) - ord('A') - (1 if c > 'I' else 0)

def gtp_chr(x: int) -> str:
    """Convert a GTP format ordinal to its letter.
    
    >>> gtp_chr(0)
    'A'
    >>> gtp_chr(24)
    'Z'

    """
    assert 0 <= x < 26
    if x >= ord('I') - ord('A'):
        x += 1
    return chr(x + ord('A'))

def ext_gtp_ord(s: str) -> int:
    """Convert extend GTP format string to board column index.

    Args:
        s (str): Extended GTP format string, which only contains letters from A to Z, excluding I.
    
    Returns:
        int: Board column index, starting from 0.
    
    >>> ext_gtp_ord("A")
    0
    >>> ext_gtp_ord("z")
    24
    >>> ext_gtp_ord("AA")
    25
    >>> ext_gtp_ord("az")
    49
    >>> ext_gtp_ord("AAA")
    650

    """
    assert len(s) > 0
    assert s.isascii()
    assert s.isalpha()
    s = s.upper()
    x = 0
    for c in s:
        x *= 25
        x += gtp_ord(c) + 1
    return x - 1

def ext_gtp_str(x: int) -> str:
    """Convert board column index to extend GTP format string.

    Args:
        x (int): Board column index, starting from 0.
    
    Returns:
        str: Extended GTP format string, which only contains uppercase letters from A to Z, excluding I.
    
    >>> ext_gtp_str(0)
    'A'
    >>> ext_gtp_str(24)
    'Z'
    >>> ext_gtp_str(25)
    'AA'
    >>> ext_gtp_str(650)
    'AAA'
    """

    assert x >= 0
    x = x + 1
    letters = []
    while x > 0:
        x, r = divmod(x, 25)
        # check for exact division and borrow if needed
        if r == 0:
            r = 25
            x -= 1
        letters.append(gtp_chr(r - 1))
    return ''.join(reversed(letters))

def coord_to_gtp(x: int | tuple, y: int | None=None, one_based=False) -> str:
    """Convert coordinates to GTP format string.

    Args:
        x (int | tuple): x coordinate or (x, y) tuple
        y (int | None, optional): y coordinate. If x is a tuple, ignore this argument. Defaults to None.
        one_based (bool, optional): Whether the coordinates are one-based. Defaults to False.
        If True, the coordinates are one-based, i.e. the lower left corner is (1, 1) instead of (0, 0).
    
    >>> coord_to_gtp(0, 0)
    'A1'
    >>> coord_to_gtp(4, 4, one_based=True)
    'D4'
    >>> coord_to_gtp((0, 0))
    'A1'
    >>> coord_to_gtp(25, 25)
    'AA26'
    """

    if isinstance(x, tuple):
        x, y = x
    if one_based:
        x -= 1
        y -= 1
    return ext_gtp_str(x) + str(y + 1)

def coord_from_gtp(s: str, one_based=False) -> tuple[int, int]:
    """Convert GTP format string to coordinates.

    Args:
        s (str): GTP format string
        one_based (bool, optional): Whether the coordinates are one-based. Defaults to False.
    
    Returns:
        tuple: (x, y) tuple
    
    >>> coord_from_gtp("A1")
    (0, 0)
    >>> coord_from_gtp("D4", one_based=True)
    (4, 4)
    >>> coord_from_gtp("AA26")
    (25, 25)
    """
    if not s.isalnum() or not s.isascii():
        raise ValueError(f"Invalid vertex string: '{s}'")
    s = s.upper()
    match = re.match(r'([A-HJ-Z]+)(\d+)', s)
    if match:
        letters, numbers = match.groups()
    else:
        raise ValueError(f"Invalid vertex string: '{s}'")
    
    x = ext_gtp_ord(letters)
    y = int(numbers) - 1
    if one_based:
        x += 1
        y += 1

    return x, y

if __name__ == "__main__":
    import doctest
    doctest.testmod()