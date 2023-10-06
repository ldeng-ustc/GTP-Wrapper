if __name__ == "__main__":
    import doctest
    from . import board, engine, katago
    doctest.testmod(board)
    doctest.testmod(engine)
    doctest.testmod(katago)
