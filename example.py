from gtp_wrapper import KataGoEngine, Vertex, Color, Move


if __name__ == "__main__":
    katago_path = r"C:/Utils/katago-v1.13.0-opencl-windows-x64/katago.exe"
    model_path = r"C:/Utils/katago-models/kata1-b18c384nbt-s5832081920-d3223508649.bin.gz"
    config_path = r"C:/Utils/katago-v1.13.0-opencl-windows-x64/gtp_custom.cfg"
    engine = KataGoEngine(katago_path, model_path, config_path)

    res = engine.protocol_version()
    print(f'> protocol_version\n{res}')
    assert res == 2

    res = engine.name()
    print(f'> name\n{res}')
    assert res == "KataGo"

    res = engine.version()
    print(f'> version\n{res}')
    assert res == "1.13.0"

    res = engine.known_command("kata-analyze")
    print(f'> known_command kata-analyze\n{res}')
    assert res == True

    res = engine.list_commands()
    print(f'> list_commands\n{res}')
    assert all([cmd in res for cmd in ["name", "version", "kata-analyze", "play", "genmove"]])

    engine.play("B", "D4")
    print(f'> play B D4')
    engine.undo()
    print(f'> undo')

    res = engine.genmove("B")
    print(f'> genmove B\n{res}')
    assert 0 <= res.x <= 18 and 0 <= res.y <= 18



