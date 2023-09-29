import os
import subprocess
import logging
import threading
import time
from queue import Queue
from collections.abc import Sequence, Generator

class GTPEngine:
    class __Command:
        def __init__(self, command: str) -> None:
            self.command: str = command
            self.response: list[str] = []
            self.finished: bool = False
            self.lock = threading.Lock()

    def __init__(self, args: Sequence[str] | str, logger_name: str | None  = None):
        """Create a new GTP engine.

        Args:
            args (Sequence | str): Program and arguments pass to subprocess.Popen
        """
        self.logger = logging.getLogger(logger_name)
        self.engine = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.lock = threading.Lock()
        self.commands = []
        self.command_queue: Queue[self.__Command] = Queue()


        def __read_stdout():
            while self.engine.poll() is None:
                active_command: self.__Command = self.command_queue.get()

                while True:
                    line = self.engine.stdout.readline().decode().strip()
                    with self.lock, active_command.lock:                       
                        active_command.response.append(line)
                        if line == '':
                            active_command.finished = True
                            break
                        
        self.__read_stdout_thread = threading.Thread(target=__read_stdout, daemon=True)
        self.__read_stdout_thread.start()

    def __send(self, message: str) -> __Command:
        """Send a message to the engine and return the index of the command in the command list.

        Args:
            message (str): Message to send

        Raises:
            RuntimeError: Failed to write to engine stdin

        Returns:
            int: Index of the command in the command list
        """
        message = message.split("#")[0]
        message = message.strip()
        if message == "":
            raise ValueError("Empty message")
        message_line = (message + "\n").encode()
        ret = self.engine.stdin.write(message_line)
        if ret != len(message_line):
            raise RuntimeError("Failed to write to engine stdin")
        self.engine.stdin.flush()
        with self.lock:
            command = self.__Command(message)
            self.commands.append(command)
            self.command_queue.put(command)
            return command


    def wait_util_finished(self, command: __Command):
        """Wait until the command is finished.
        For command with persistent output, must manually stop command before waiting, otherwise it will block forever.

        Args:
            command (__Command): The command to wait for
        """
        while True:
            with self.lock:
                if command.finished:
                    break
            time.sleep(0.01)

    def send_command(self, command: str) -> list[str]:
        """Send a command to the engine and return the response.
        CANNOT used for command with persistent output (e.g. lz-analyze or kata-analyze).
        For command with persistent output, use send_command_persistent instead.

        Args:
            command (str): Command to send

        Returns:
            str: Response from the engine
        """
        cmd = self.__send(command)
        self.wait_util_finished(cmd)
        return cmd.response.copy()

    def send_command_persistent(self, command: str) -> Generator[str, None, None]:
        cmd = self.__send(command)

        def __generate_response():
            i = 0
            while True:
                need_wait = True
                with cmd.lock:
                    if i < len(cmd.response):
                        yield cmd.response[i]
                        i += 1
                        need_wait = False
                    elif cmd.finished:
                        break
                if need_wait:
                    time.sleep(0.01)
        return __generate_response()

    def stop_persistent(self):
        """Stop a command with persistent output. Actually send an empty line to the engine.
        """
        self.engine.stdin.write(b'\n')
        self.engine.stdin.flush()

if __name__ == "__main__":
    katago_path = r"C:/Utils/katago-v1.13.0-opencl-windows-x64/katago.exe"
    model_path = r"C:/Utils/katago-models/kata1-b18c384nbt-s5832081920-d3223508649.bin.gz"
    config_path = r"C:/Utils/katago-v1.13.0-opencl-windows-x64/gtp_custom.cfg"
    engine = GTPEngine([katago_path, "gtp", "-model", model_path, "-config", config_path])
    res = engine.send_command("protocol_version")
    print(res)

    lines = engine.send_command_persistent("lz-analyze 100")
    cnt = 0
    for line in lines:
        print(line)
        cnt += 1
        if cnt == 5:
            engine.stop_persistent()
    print("Done")

    