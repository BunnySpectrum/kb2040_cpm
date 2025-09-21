from __future__ import annotations
import asyncio
import ast
import sys
import time
import inspect
import dataclasses
import enum
from typing import List, Optional, Iterable, Union


class BiosWriteDest(enum.Enum):
    DISPLAY = enum.auto()


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
            err_string = f'{cmd._raw_value.split(' ')[0].upper()}?'
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