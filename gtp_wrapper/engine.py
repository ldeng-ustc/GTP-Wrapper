import subprocess
import logging
import threading
import time
from typing import Any
from queue import Queue
from collections.abc import Sequence, Iterable

if __name__ == "__main__":
    from board import Vertex, Color, Move, color_from_str
else:
    from .board import Vertex, Color, Move, color_from_str

class GTPEngine:
    class __Command:
        def __init__(self, command: str) -> None:
            self.command: str = command
            self.response: list[str] = []
            self.ready: bool = False        # True if the command is ready to be read
            self.error: bool = False 
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
                # print(f'get command: "{active_command.command}"')
                while True:
                    line = self.engine.stdout.readline().decode().strip()
                    # print(f'read line: "{line}"')
                    with self.lock, active_command.lock:
                        line = line.strip()
                        empty_line = line == ""
                        if not active_command.ready:
                            if line[0] != "=" and line[0] != "?":
                                raise RuntimeError(f"Expected response start with '=' or '?', got '{line[0]}'")
                            active_command.error = line.startswith("?")
                            line = line[1:]
                            active_command.ready = True
                        
                        if empty_line:
                            active_command.finished = True
                            break

                        active_command.response.append(line.strip())
                # print(f'finish command: "{active_command.command}"')

                        
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


    def __wait_ready(self, command: __Command):
        """Wait until the command is ready to be read. (First line of response is ready.)

        Args:
            command (__Command): The command to wait for
        """
        while True:
            with self.lock:
                if command.ready:
                    break
            time.sleep(0.01)

    def send_command(self, command: str) -> tuple[bool, Iterable[str]]:
        """Send a command to the engine and return the response.
        For command will run forever (such as lz-analyze), must manually call stop_persistent()
        or send a new command to stop it, otherwise it will iterate forever.

        Args:
            command (str): Command to send

        Returns:
            str: Response from the engine
        """
        cmd = self.__send(command)
        self.__wait_ready(cmd)
        ok = not cmd.error

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
        
        return ok, __generate_response()

    def __wait_finished(self, command: __Command):
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
        _, res = self.send_command("protocol_version")
        return int(next(res))
    
    def name(self) -> str:
        """name command

        Returns:
            str: Name of the engine. E.g. "GNU Go", "GoLois", "Many Faces of Go". 
            The name does not include any version information, which is provided by the version command.
        """
        _, res = self.send_command("name")
        return next(res)
    
    def version(self) -> str:
        """version command

        Returns:
            str: Version of the engine. E.g. "3.1.33", "10.5". 
            Engines without a sense of version number should return the empty string.
        """
        _, res = self.send_command("version")
        return next(res)
    
    def known_command(self, command: str) -> bool:
        """known_command command

        Args:
            command (str): Name of a command

        Returns:
            bool: True if the command is known by the engine, False otherwise
        """
        _, res = self.send_command("known_command " + command)
        return next(res) == "true"
    
    def list_commands(self) -> list[str]:
        """list_commands command

        Returns:
            list[str]: List of all commands known by the engine. 
            Include all known commands, including required ones and private extensions.
        """
        _, res = self.send_command("list_commands")
        return list(res)
    
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
        ok, res = self.send_command(f"boardsize {size}")
        if not ok:
            raise ValueError(next(res))

    
    def clear_board(self) -> None:
        """clear_board command. The board is cleared, the number of captured stones is 
        reset to zero for both colors and the move history is reset to empty.
        """
        self.send_command("clear_board")
    
    def komi(self, new_komi: float) -> None:
        """komi command. The komi is set to the specified value.

        The engine must accept the komi even if it should be ridiculous.

        Args:
            komi (float): New value of komi.
        
        Raises:
            ValueError: Syntax error
        """
        ok, res = self.send_command(f"komi {new_komi}")
        if not ok:
            raise ValueError(next(res))
    
    def play(self, move_or_color, x=None, y=None, one_based=False) -> None:
        """play command. A stone of the requested color is played at the requested vertex. 
        The number of captured stones is updated if needed and the move is added to the move history.
        """
        if isinstance(move_or_color, Move):
            move = move_or_color
        else:
            move = Move(move_or_color, x, y, one_based)
        ok, res = self.send_command(f"play {move}")
        if not ok:
            raise ValueError(next(res))
    
    def genmove(self, color: Color | str) -> Vertex | str:
        """genmove command. A stone of the requested color is played where the engine chooses. 
        The number of captured stones is updated if needed and the move is added to the move history.

        Args:
            color (Color | str): Color of the stone to play

        Returns:
            Vertex | str: The vertex where the engine played, or "resign" if the engine resigns.
            	Notice that Vertex(x=None, y=None) is a valid vertex (means "pass") and will be returned 
                if the engine wants to pass. "resign" will be return if engine want to give up the game. 
                The controller is allowed to use this command for either color, regardless who played the last move.
        """
        if isinstance(color, str):
            color = color_from_str(color)
        ok, res = self.send_command(f"genmove {color}")
        if not ok:
            raise ValueError(next(res))
        str_res = next(res)
        if str_res == "resign":
            return "resign"
        else:
            return Vertex(str_res)
    
    def undo(self) -> None:
        """undo command. The board configuration and the number of captured stones are 
        reset to the state before the last move. The last move is removed from the move history.

        If you want to take back multiple moves, use this command multiple times.
        The engine may fail to undo if the move history is empty or if the engine 
        only maintains a partial move history, which has been exhausted by previous undos. 
        It is never possible to undo handicap placements. Use clear_board if you want to 
        start over. An engine which never is able to undo should not include this command 
        among its known commands.
        """
        ok, res = self.send_command("undo")
        if not ok:
            raise ValueError(next(res))


    
    # TODO: define Vertex, Color and Move class
    # Correctly parse the response, use (bool, list[str]) as command return type
    # remove first character of the response ('=' or '?'). If it is '=', return True, otherwise return False
        
    

    