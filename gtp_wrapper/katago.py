from typing import NamedTuple

if __name__ == "__main__":
    from board import Vertex, Color, Move, color_from_str
    from engine import GTPEngine
else:
    from .board import Vertex, Color, Move, color_from_str
    from .engine import GTPEngine

class SearchList(NamedTuple):
    player: Color
    vertex_list: list[Vertex]
    until_depth: int

    def __str__(self) -> str:
        return f'{self.player} {",".join([str(v) for v in self.vertex_list])} {self.until_depth}'

class LzAnalyzeMoveInfo(NamedTuple):
    move: Vertex = None         # The move being analyzed.
    visits: int = None          # The number of visits invested into the move so far.
    winrate: float = None       # The winrate of the move so far.
    prior: float = None         # The policy prior of the move.
    lcb: float = None           # The LCB of the move, current implementation doesn't strictly account for the 0-1 bounds.
    order: int = None           # KataGo's ranking of the move. 0 is the best, 1 is the next best, and so on.
    pv: list[Vertex] = None     # The principal variation following this move. May be of variable length or even empty.

def parse_lz_analyze_info(words: list[str], st: int) -> (int, list[LzAnalyzeMoveInfo]):
    if words[st] != 'info':
        raise ValueError(f"Respone format error at {st}: '{words[st]}', expected 'info'")
    i = st + 1
    info_dict = {}
    while i < len(words):
        if words[i] == 'move':
            info_dict['move'] = Vertex(words[i+1])
            i += 2
        elif words[i] == 'visits':
            info_dict['visits'] = int(words[i+1])
            i += 2
        elif words[i] == 'winrate':
            info_dict['winrate'] = float(int(words[i+1]) / 10000)
            i += 2
        elif words[i] == 'prior':
            info_dict['prior'] = float(int(words[i+1]) / 10000)
            i += 2
        elif words[i] == 'lcb':
            info_dict['lcb'] = float(int(words[i+1]) / 10000)
            i += 2
        elif words[i] == 'order':
            info_dict['order'] = int(int(words[i+1]))
            i += 2
        elif words[i] == 'pv':
            pv = []
            i += 1
            while i < len(words):
                try:
                    v = Vertex(words[i])
                except ValueError:
                    break
                pv.append(v)
                i += 1
            info_dict['pv'] = pv
        else:
            break
    res = LzAnalyzeMoveInfo(**info_dict)
    return i, res
    

def parse_lz_analyze_line(line: str) -> list[LzAnalyzeMoveInfo]:
    line = line.strip()
    words = line.split()
    if len(words) < 1:
        return []
    
    res = []
    i = 0
    while i < len(words):
        if words[i] == 'info':
            i, info = parse_lz_analyze_info(words, i)
            res.append(info)
        else:
            i += 1
    return res


            
    

class KataGoEngine(GTPEngine):
    """Wrapper for KataGo GTP engine. 

    See https://github.com/lightvector/KataGo/blob/master/docs/GTP_Extensions.md for more details.
    """
    def __init__(self, katago_path: str, model_path: str, config_path: str, logger_name: str=None):
        """Initialize KataGo engine.

        Args:
            katago_path (str): Path to KataGo executable.
            model_path (str): Path to KataGo model.
            config_path (str): Path to KataGo config.
        """
        super().__init__([katago_path, "gtp", "-model", model_path, "-config", config_path], logger_name)



    def lz_analyze(player: Color=None, internal: int=None, minmoves: int=None, maxmoves: int=None, 
                    avoid: SearchList | list[SearchList]=None, 
                    allow: SearchList | list[SearchList]=None,
                    **kwargs):
        """Perform a lz-analyze command. Begin searching and optionally outputting live analysis to stdout. 
        Assumes the normal player to move next unless otherwise specified. 

        Args:
            player (Color, optional): Player to move next. Defaults to None (normal player).
            internal (int, optional): Output a line every this many centiseconds. Defaults to None (never output).
            minmoves (int, optional): Output stats for at least N different legal moves if possible (will likely 
                cause KataGo to output stats on 0-visit moves). Defaults to None.
            maxmoves (int, optional): Output stats for at most N different legal moves 
                (NOTE: Leela Zero does NOT currently support this field) Defaults to None.
            avoid (SearchList | list[SearchList], optional): Prohibit the search from exploring the specified moves
                for the specified player, until until_depth deep in the search. May be supplied multiple times with 
                different until_depth for different sets of moves. The behavior is unspecified if a move is specified 
                more than once with different until_depth. Defaults to None.
            allow (SearchList, optional): Equivalent to avoid on all vertices EXCEPT for the specified vertices. 
            Can only be specified once, and cannot be specified at the same time as avoid. Defaults to None.
        """

        cmd = ["lz-analyze"]
        if player is not None:
            cmd.append(str(Color(player)))
        if internal is not None:
            cmd.append(str(internal))
        if minmoves is not None:
            cmd.append(f'minmoves {minmoves}')
        if maxmoves is not None:
            cmd.append(f'maxmoves {maxmoves}')
        if avoid is not None:
            if isinstance(avoid, SearchList):
                avoid = [avoid]
            for avoid_list in avoid:
                cmd.append(f'avoid {str(avoid_list)}')
        if allow is not None:
            if isinstance(allow, SearchList):
                allow = [allow]
            for allow_list in allow:
                cmd.append(f'allow {str(allow_list)}')
