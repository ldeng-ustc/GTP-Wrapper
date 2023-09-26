import os
import subprocess
from typing import Sequence, Generator

class GTPEngine:

    def __init__(self, args: Sequence[str] | str):
        """Create a new GTP engine.

        Args:
            args (Sequence | str): Program and arguments pass to subprocess.Popen
        """
        self.engine = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def send(self, message: str | bytes) -> None:
        """Send a message to the engine. An new line is automatically appended.

        Args:
            message (str | bytes): Message to send
        """
        if isinstance(message, str):
            message = message.encode().strip()
        self.engine.stdin.write(message + b"\n")
        self.engine.stdin.flush()

    def recv(self) -> str:
        """Receive one line from the engine. The new line is automatically stripped.

        Returns:
            str: Message received
        """
        while True:
            print("Waiting for line")
            line = self.engine.stdout.readline()
            if not line:
                break
            yield line.decode().strip()
    

if __name__ == "__main__":
    katago_path = r"/mnt/c/Utils/katago-v1.13.0-opencl-windows-x64/katago.exe"
    model_path = r"/mnt/c/Utils/katago-models/kata1-b18c384nbt-s5832081920-d3223508649.bin.gz"
    config_path = r"/mnt/c/Utils/katago-v1.13.0-opencl-windows-x64/gtp_custom.cfg"
    engine = GTPEngine([katago_path, "gtp", "-model", model_path, "-config", config_path])
    for line in engine.recv():
        print(line)
        if line == "= ":
            engine.send("genmove b")
        elif line == "? ":
            engine.send("quit")
            break
    engine.engine.wait()