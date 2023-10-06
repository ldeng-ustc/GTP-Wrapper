import re
from enum import Enum

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



def coord_to_gtp(x: int, y: int) -> str:
    """Convert coordinates to GTP format string.

    Args:
        x (int): col index, zero-based
        y (int): row index, zero-based
    
    >>> coord_to_gtp(0, 0)
    'A1'
    >>> coord_to_gtp(25, 25)
    'AA26'
    """
    return ext_gtp_str(x) + str(y + 1)

def coord_from_gtp(s: str) -> tuple[int, int]:
    """Convert GTP format string to coordinates.

    Args:
        s (str): GTP format string
    
    Returns:
        tuple: (x, y) tuple
    
    >>> coord_from_gtp("A1")
    (0, 0)
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

    return x, y



# def vertex(x: int | VertexLike, y: int | None=None, one_based=False) -> tuple[int, int] | None:
#     """
#         In GTP protocol (version 2), a `vertex` is a board coordinate, or the string "pass".
#         In this module, a `vertex` is a (x, y) tuple, as the coordinate, or None as "pass".
#         For convenience, this function can convert different type of coordinates to standard (x, y) tuple.
#     """


VertexLike: type = tuple[int, int] | str | None
class Vertex:
    """A vertex is a board coordinate.
    """

    def __init__(self, x: int | VertexLike, y: int | None=None, one_based=False):
        """Create standard Vertex class from diffent type of coordinates.

        Args:
            x (int | VertexLike): col index, or (x, y) tuple, or GTP format string, or None as "pass"
            y (int | None, optional): row index. If x is a tuple or str, ignore this argument. Defaults to None.
            one_based (bool, optional): When init Vertex by coordinate, determine whether the parameters be 
            considered as one-based. Ignored if x is str. Defaults to False.
        
        >>> a = Vertex(0, 0); a
        Vertex(x=0, y=0)
        >>> a = Vertex(4, 4, one_based=True); a
        Vertex(x=3, y=3)
        >>> a = Vertex((0, 0)); a
        Vertex(x=0, y=0)
        >>> a = Vertex((4, 4), one_based=True); a
        Vertex(x=3, y=3)
        >>> a = Vertex("A1"); a
        Vertex(x=0, y=0)
        >>> a = Vertex("pass"); a
        Vertex(x=None, y=None)
        >>> a = Vertex(None); a
        Vertex(x=None, y=None)


        """
        if isinstance(x, str):
            if x == "pass":
                self.x = None
                self.y = None
                return
            else:
                x, y = coord_from_gtp(x)
                self.x = x
                self.y = y
                return
        elif isinstance(x, Vertex):
            self.x = x.x
            self.y = x.y
            return
        elif isinstance(x, tuple):
            x, y = x

        if one_based:
            x -= 1
            y -= 1
        self.x = x
        self.y = y
    
    def gtp_str(self) -> str:
        return coord_to_gtp(self.x, self.y)

    def __str__(self) -> str:
        return self.gtp_str()
    
    def __repr__(self) -> str:
        return f"Vertex(x={self.x}, y={self.y})"

class Color(Enum):
    """Color of a stone.
    """
    BLACK = 1
    WHITE = 2

    def __str__(self) -> str:
        return 'B' if self == Color.BLACK else 'W'
    
    def __repr__(self) -> str:
        return f'Color.{self.name}'

def color_from_str(s: str) -> Color:
    """Convert a string to Color enum.
    
    Args:
        s (str): 'B' or 'W', 'BLACK' or 'WHITE' for black or white.
        Case insensitive.
    
    Returns:
        Color: Color enum.
    
    >>> color_from_str("B")
    Color.BLACK
    >>> color_from_str("W")
    Color.WHITE
    """
    c = s.upper()
    if c == "B" or c == "BLACK":
        return Color.BLACK
    elif c == "W" or c == "WHITE":
        return Color.WHITE
    else:
        raise ValueError(f"Invalid color: '{s}'")

class Move:
    def __init__(self, color: Color | str, x: int | VertexLike, y: int | None=None, one_based=False) -> None:
        """Create a Move object, a move is a color and a vertex.
        
        Args:
            color (Color | str): Color of the move, 'B' or 'W' for black or white.
            x (int | VertexLike): column index or a vertex-like object, see Vertex class for details.
            y (int | None, optional): row index. Only used when x is int. Defaults to None.
            one_based (bool, optional): Determine whether the parameters be considered as one-based.
            See Vertex class for details. Defaults to False.
        
        >>> a = Move(Color.BLACK, 0, 0); a
        Move(color=Color.BLACK, vertex=Vertex(x=0, y=0))
        >>> a = Move(Color.BLACK, 4, 4, one_based=True); a
        Move(color=Color.BLACK, vertex=Vertex(x=3, y=3))
        >>> a = Move('B', (0, 0)); a
        Move(color=Color.BLACK, vertex=Vertex(x=0, y=0))
        """
        if isinstance(color, str):
            self.color = color_from_str(color)
        elif isinstance(color, Color):
            self.color = color
        else:
            raise ValueError(f"Invalid color: '{color}'")
        
        self.vertex = Vertex(x, y, one_based)
    
    def __str__(self) -> str:
        return f"{self.color} {self.vertex}"
    
    def __repr__(self) -> str:
        return "Move(color={}, vertex={})".format(repr(self.color), repr(self.vertex))

