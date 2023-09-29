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
    
    def protocol_version(self) -> int:
        """protocol_version command

        Returns:
            int: Version of the GTP Protocol
        """
        res = self.send_command("protocol_version")
        return int(res[0])
    
    def name(self) -> str:
        """name command

        Returns:
            str: Name of the engine. E.g. "GNU Go", "GoLois", "Many Faces of Go". 
            The name does not include any version information, which is provided by the version command.
        """
        res = self.send_command("name")
        return res[0]
    
    def version(self) -> str:
        """version command

        Returns:
            str: Version of the engine. E.g. "3.1.33", "10.5". 
            Engines without a sense of version number should return the empty string.
        """
        res = self.send_command("version")
        return res[0]
    
    def known_command(self, command: str) -> bool:
        """known_command command

        Args:
            command (str): Name of a command

        Returns:
            bool: True if the command is known by the engine, False otherwise
        """
        res = self.send_command("known_command " + command)
        return res[0] == "true"
    
    def list_commands(self) -> list[str]:
        """list_commands command

        Returns:
            list[str]: List of all commands known by the engine. 
            Include all known commands, including required ones and private extensions.
        """
        res = self.send_command("list_commands")
        return res
    
    def quit(self) -> None:
        """quit command, do not send any more commands after this
        """
        self.send_command("quit")
        self.engine.wait()
        self.__read_stdout_thread.join()
        self.engine = None
    
    def boardsize(self, size: int) -> None:
        """boardsize command. The board size is changed. The board configuration, 
        number of captured stones, and move history become arbitrary.

        
        In GTP version 1 this command also did the work of clear_board. This may or may not 
        be true for implementations of GTP version 2. Thus the controller must call clear_board 
        explicitly. Even if the new board size is the same as the old one, the board 
        configuration becomes arbitrary.

        Args:
            size (int): New size of the board.
        
        Raises:
            ValueError: Invalid size
        """
        res = self.send_command(f"boardsize {size}")
        if res[0].startswith("?"):
            raise ValueError(res[0])
    
    def clear_board(self) -> None:
        """clear_board command. The board is cleared, the number of captured stones is 
        reset to zero for both colors and the move history is reset to empty.
        """
        self.send_command("clear_board")
    
    def komi(self, komi: float) -> None:
        """komi command. The komi is set to the specified value.

        The engine must accept the komi even if it should be ridiculous.

        Args:
            komi (float): New value of komi.
        
        Raises:
            ValueError: Syntax error
        """
        res = self.send_command(f"komi {komi}")
        if res[0].startswith("?"):
            raise ValueError(res[0])
    
    # TODO: define Vertex, Color and Move class
    # Correctly parse the response, use (bool, list[str]) as command return type
    # remove first character of the response ('=' or '?'). If it is '=', return True, otherwise return False
        
    
    



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

    