from __future__ import annotations
import asyncio
import ast
import sys
import time
import inspect
import dataclasses
import enum
from typing import List, Optional, Iterable, Union

async def blink(pin, count):
    index = 0
    for _ in range(count):
        print(f'pin: {index}')
        index += 1
        await asyncio.sleep(1)

    frame = inspect.currentframe()
    print(f"Done: {frame.f_code.co_name}, {inspect.getargvalues(frame)}")

"""
Drives: 16  (A - P)
- up to 8MB each
- 128MB total file size
"65536 records of an 8MB file"

Able to copy files from one user to another

System parts:
- BIOS (hw-dependent)
    disk drives
    teletype
    CRT
    paper tape punch/reader
    user-defined peripherals 
- Basic Disc Operating System
    disk/file management
- Console Command Processor
    symbolic interface between console and CP/M
- Transient Program Area


"""
def _build_disks(count):
    names = []
    values = []
    START_NAME = 'A'
    for index in range(count):
        names.append(chr(ord(START_NAME) + index))
        values.append(index)

    return names, values

DISK_NAMES, DISK_VALUES = _build_disks(16)
# DiskDrive = enum.Enum('DiskDrive', dict(zip(DISK_NAMES, DISK_VALUES)))

def do_the_thing(d, items):
    for k, v in items:
        d[k] = v

class DiskDrive(enum.Enum):
    do_the_thing(locals(), list(zip(DISK_NAMES, DISK_VALUES)))

    def __str__(self):
        return str(self.name)

    @classmethod
    def from_str(cls, value: str) -> DiskDrive:
        for entry in DiskDrive:
            if value.upper() == entry.name:
                return entry
        
        raise ValueError(f"Invalid disk name: {value}")

    
def _build_users(count):
    names = []
    values = []
    for index in range(count):
        names.append(f'USR{index}')
        values.append(index)

    return names, values

USER_NAMES, USER_VALUES = _build_users(16)

class User(enum.Enum):
    do_the_thing(locals(), list(zip(USER_NAMES, USER_VALUES)))

    def __str__(self):
        return str(self.value)


class BdosOpcode(enum.Enum):
    SEARCH = 'search'
    OPEN = 'open'
    CLOSE = 'close'
    RENAME = 'rename'
    READ = 'read'
    WRITE = 'write'
    SELECT = 'select'


@dataclasses.dataclass
class CpmVersion:
    major: int
    minor: int

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}'



class CcpMessage:
    def __init__(self, message: Optional[str] = None, auto_lock: bool = True):
        self.locked = False
        self.entries: List[str] = []

        if message is not None:
            self.append(message)

        if auto_lock:
            self.lock()

    def append(self, entry: str):
        if self.locked:
            return

        self.entries.append(entry)

    def lock(self):
        self.locked = True

    def entries(self) -> Iterable[str]:
        return iter(self.entries)

    def is_empty(self) -> bool:
        return len(self.entries) == 0

class CcpOpcode(enum.Enum):
    ERA = 'era' # era afn
    DIR = 'dir' # dir afn
    REN = 'ren' # ren ufn1=ufn2
    SAVE = 'save' # save n ufn
    TYPE = 'type' # type ufn
    USER = 'user' # user n

    # python-specific
    # replace w/ real program like runcpm?ic
    EXIT = 'exit' 
    PY = 'py'
    ERR = 'err' # print current logged error strign 

    def __str__(self):
        return str(self.value)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return super().__eq__(other)
        elif isinstance(other, str):
            return other.lower() == str(self)
        else:
            return False


class CcpCommand:
    DELIM = ' '
    def __init__(self, raw_value: str):
        self._raw_value = raw_value
        self._opcode: Optional[CcpOpcode] = None
        self._parse_raw_value()
    
    def _parse_raw_value(self):
        symbols = self._raw_value.split(CcpCommand.DELIM)

        for opcode in CcpOpcode:
            if symbols[0] == opcode:
                self._opcode = opcode

    def as_message(self) -> CcpMessage:
        return CcpMessage(self._raw_value)


    def is_quit(self) -> bool:
        return self._opcode == CcpOpcode.EXIT
    
    def is_err(self) -> bool:
        return self._opcode == CcpOpcode.ERR

    def is_cpm(self) -> bool:
        return self._opcode is not None

    def is_python(self) -> bool:
        try:
            ast.parse(self._raw_value, mode='single')
            return True
        except SyntaxError:
            return False

class BiosWriteDest(enum.Enum):
    DISPLAY = enum.auto()

@dataclasses.dataclass
class CpmState:
    drive: DiskDrive
    version: CpmVersion
    user: User
    prompt: str = ">"
    error_message: Optional[CcpMessage] = None

    def log_error(self, msg: Optional[CcpMessage]):
        self.error_message = msg

class Bios:
    def __init__(self, state: CpmState):
        self._printer = print
        self._state = state
        self._error_message: Optional[CcpMessage] = None

    def _write(self, message: CcpMessage, dest: BiosWriteDest, dest_info = None):
        if dest == BiosWriteDest.DISPLAY:
            for entry in message.entries:
                self._printer(f'{entry}')

    def print(self, message: CcpMessage):
        if not message.is_empty():
            self._write(message=message, dest=BiosWriteDest.DISPLAY)

    def set_error_message(self, msg: CcpMessage):
        self._error_message = msg

    def print_error(self):
        msg = self._state._error_message
        if msg is not None:
            self.print(msg)
        else:
            self.print(CcpMessage('No error logged.'))
    
    async def get_input(self) -> CcpCommand:
        # prefix = f'{self._state.drive}{self._state.user}{self._state.prompt}'
        # await asyncio.to_thread(sys.stdout.write, prefix)
        # value = await asyncio.to_thread(sys.stdin.readline)
        prefix = f'{self._state.drive}{self._state.user}{self._state.prompt}'
        value = await asyncio.to_thread(input, prefix)
        return CcpCommand(raw_value=value.strip())



class FileSpec:
    DELIM = set(['.'])
    DRIVE_SUFFIX = set([':'])
    WILDCARD_SINGLE = set(['?'])
    WILDCARD_ALL = set(['*'])
    RESERVED_CHARS = set(['<', '>', ',', ';', '=', '[', ']', '%', '|', '(', ')', '/', '\\'])

    INVALID_DRIVE_CHARS = WILDCARD_ALL | WILDCARD_SINGLE | RESERVED_CHARS  | DELIM

    def __init__(self, filename: str, extension: str, drive: DiskDrive, user: User):
        self._filename = filename
        self._extension = extension
        self._drive = drive
        self._user = user

        self._filename_is_afn = any(char in FileSpec.WILDCARD_SINGLE for char in self._filename)
        self._ext_is_afn = any(char in FileSpec.WILDCARD_SINGLE for char in self._extension)
        self._is_afn = self._filename_is_afn or self._ext_is_afn

    def is_afn(self) -> bool:
        return self._is_afn
    
    def is_ufn(self) -> bool:
        return not self.is_afn()

    def __str__(self) -> str:
        return f'{self._drive}{self._user}:{self._filename}.{self._extension}'

    @classmethod
    def from_str(cls, value: str, state: CpmState) -> Optional[FileSpec]:
        """
        Valid forms
            <drive>:<filename>.<extension>
            <filename>.<extension>
            <filename>

        Forms not explicity called out in manual, but worked in RunCpm
            <drive>:
            <filename>.
        

        Filename may be 1-8 characters
        Extension may be 1-3 characters
        Drive is always 1 character
        ? is a wildcard character
        * is expanded to ???????? or ??? if it is in the filename or extension position, respectively
        If ? appears in filename or extension, the filespec is an 'ambiguous filespec' (afn).
        else it is an 'unambiguous filespec' (ufn)
        Following characters are not allowed in filename or extensions for ufn
            < > . , ; : = ? * [ ] % | ( ) / \

        """
        class ParseState(enum.Enum):
            DRIVE = enum.auto()
            FILENAME = enum.auto()
            EXT = enum.auto()
            DONE = enum.auto()
            ERROR = enum.auto()

        buffer = ''
        raw_filename = None
        raw_ext = None
        raw_drive = None
        for char in value:
            if raw_drive is None:
                if char in FileSpec.DRIVE_SUFFIX:
                    raw_drive = buffer
                    buffer = ''
                elif char in FileSpec.DELIM:
                    # default to current drive
                    raw_drive = state.drive
                    raw_filename = buffer
                    buffer = ''
                else:
                    buffer += char
            elif raw_filename is None:
                if char in FileSpec.DELIM:
                    raw_filename = buffer
                    buffer = ''
                else:
                    buffer += char
            elif raw_ext is None:
                buffer += char
        else:
            if raw_drive is None:
                # never saw : or ., so must be filename
                raw_drive = state.drive
                raw_filename = buffer
                raw_ext = ''
            elif raw_filename is None:
                # saw a drive, but no .
                raw_filename = buffer
                raw_ext = ''
            else:
                # we're left w/ the extension
                raw_ext = buffer

        """
        Invalid cases
            - has ext, but no filename
        """
        err_msg = CcpMessage(auto_lock=False)
        dbg_msg = CcpMessage(auto_lock=False)
        drive = None
        if isinstance(raw_drive, DiskDrive):
            drive = raw_drive
        else:
            try:
                drive = DiskDrive.from_str(raw_drive)
            except ValueError:
                pass
        if drive is None:
            err_msg.append(f'Invalid drive: {raw_drive}')
        else:
            dbg_msg.append(f'{drive=}')

        dbg_msg.append(f'{raw_filename=}')
        dbg_msg.append(f'{raw_ext=}')
        dbg_msg.lock()

        if not err_msg.is_empty():
            state.log_error(err_msg)
            return None
        else:
            return FileSpec(filename=raw_filename, extension=raw_ext, drive=drive, user=state.user)

class Tpa:
    def __init__(self, state: CpmState):
        self.state = state
        self.running = True

    def push_input(self, value: str):
        pass

    def pop_output(self) -> CcpMessage:
        pass

    def is_running(self) -> bool:
        return self.running
    
    def terminate(self):
        self.running = False

class ProgramDir(Tpa):
    # Equivalent to loading the program
    def __init__(self, state):
        super().__init__(state)
        self.output: CcpMessage = CcpMessage(f'No file.') 

    def push_input(self, value: str):
        if value == '':
            # print contents of director
            self.output = CcpMessage(f'Print dir {state.drive}.')
        else:
            # we should have a filespec
            filespec = FileSpec.from_str(value=value, state=self.state)
            if filespec is None:
                self.output = CcpMessage('Invalid filespec.')
            else:
                self.output = CcpMessage(f'List filespec {filespec}')

    def pop_output(self) -> CcpMessage:
        return self.output
        


state = CpmState(drive=DiskDrive.A, 
                 version=CpmVersion(major=2, minor=0), 
                 user = User.USR0)
bios = Bios(state=state)

async def ccp_loop():
    def boot_message(state: CpmState) -> CcpMessage:
        return CcpMessage(f'CP/M VER {state.version}')        

    # ccp_locals = {}

    bios.print(boot_message(state))
    while True:
        cmd = await bios.get_input()
        if cmd.is_quit():
            break

        if cmd.is_err():
            bios.print_error()
            continue

        if cmd.is_cpm():
            bios.print(CcpMessage(f'CPM: {cmd._opcode}'))
            if cmd._opcode == CcpOpcode.DIR:
                dir = ProgramDir(state=state)
                dir.push_input(cmd._raw_value[4:])
                bios.print(dir.pop_output())



            continue

        # if cmd.is_python():
        #     try:
        #         exec(cmd._raw_value, globals(), ccp_locals)
        #     except Exception as err:
        #         bios.print(CcpMessage(f'ERR: {err}'))
        #     continue

        # print error
        err_string = '?'
        try:
            err_string = f'{cmd._raw_value.split(" ")[0].upper()}?'
        except Exception:
            pass

        bios.print(CcpMessage(err_string))


async def main():
    tasks = []
    # tasks.append(asyncio.create_task(blink(pin="test", count=5)))
    tasks.append(asyncio.create_task(ccp_loop()))
    await asyncio.gather(*tasks)

    print("Done: main()")

if __name__ == '__main__':
    asyncio.run(main())
    print("Goodbye!")