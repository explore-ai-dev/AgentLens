"""Windows Textual driver compatibility for IME committed Unicode input.

Textual 8.2.8 drops KEY_EVENT_RECORDs with control state and virtual-key 0.
Windows can use that shape for IME commits, even when UnicodeChar is populated.
"""

from __future__ import annotations

import asyncio
import sys
from threading import Event, Thread
from typing import TYPE_CHECKING, Callable

from textual.driver import Driver
from textual.drivers import win32
from textual.drivers._writer_thread import WriterThread

from firstcoder.windows_input_compat import should_drop_key_event

if TYPE_CHECKING:
    from textual.app import App


class _ImeEventMonitor(win32.EventMonitor):
    """Textual's Windows monitor with the IME-safe key-record filter."""

    def run(self) -> None:
        exit_requested = self.exit_event.is_set
        parser = win32.XTermParser(debug=win32.constants.DEBUG)

        try:
            read_count = win32.wintypes.DWORD(0)
            hIn = win32.GetStdHandle(win32.STD_INPUT_HANDLE)

            MAX_EVENTS = 1024
            KEY_EVENT = 0x0001
            WINDOW_BUFFER_SIZE_EVENT = 0x0004

            arrtype = win32.INPUT_RECORD * MAX_EVENTS
            input_records = arrtype()
            ReadConsoleInputW = win32.KERNEL32.ReadConsoleInputW
            keys: list[str] = []
            append_key = keys.append

            while not exit_requested():
                for event in parser.tick():
                    self.process_event(event)

                if win32.wait_for_handles([hIn], 100) is None:
                    continue

                ReadConsoleInputW(
                    hIn, win32.byref(input_records), MAX_EVENTS, win32.byref(read_count)
                )
                read_input_records = input_records[: read_count.value]

                del keys[:]
                new_size: tuple[int, int] | None = None

                for input_record in read_input_records:
                    event_type = input_record.EventType
                    if event_type == KEY_EVENT:
                        key_event = input_record.Event.KeyEvent
                        key = key_event.uChar.UnicodeChar
                        if key_event.bKeyDown:
                            if should_drop_key_event(
                                key_event.dwControlKeyState,
                                key_event.wVirtualKeyCode,
                                key,
                            ):
                                continue
                            append_key(key)
                    elif event_type == WINDOW_BUFFER_SIZE_EVENT:
                        size = input_record.Event.WindowBufferSizeEvent.dwSize
                        new_size = (size.X, size.Y)

                if keys:
                    for event in parser.feed(
                        "".join(keys).encode("utf-16", "surrogatepass").decode("utf-16")
                    ):
                        self.process_event(event)
                if new_size is not None:
                    self.on_size_change(*new_size)

        except Exception as error:
            self.app.log.error("EVENT MONITOR ERROR", error)


class WindowsDriver(Driver):
    """Textual Windows driver with IME committed-character compatibility."""

    def __init__(
        self,
        app: App,
        *,
        debug: bool = False,
        mouse: bool = True,
        size: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(app, debug=debug, mouse=mouse, size=size)
        self._file = sys.__stdout__
        self.exit_event = Event()
        self._event_thread: Thread | None = None
        self._restore_console: Callable[[], None] | None = None
        self._writer_thread: WriterThread | None = None

    @property
    def can_suspend(self) -> bool:
        return True

    def write(self, data: str) -> None:
        assert self._writer_thread is not None, "Driver must be in application mode"
        self._writer_thread.write(data)

    def _enable_mouse_support(self) -> None:
        if not self._mouse:
            return
        write = self.write
        write("\x1b[?1000h")
        write("\x1b[?1003h")
        write("\x1b[?1015h")
        write("\x1b[?1006h")
        self.flush()

    def _disable_mouse_support(self) -> None:
        if not self._mouse:
            return
        write = self.write
        write("\x1b[?1000l")
        write("\x1b[?1003l")
        write("\x1b[?1015l")
        write("\x1b[?1006l")
        self.flush()

    def _enable_bracketed_paste(self) -> None:
        self.write("\x1b[?2004h")

    def _disable_bracketed_paste(self) -> None:
        self.write("\x1b[?2004l")

    def start_application_mode(self) -> None:
        loop = asyncio.get_running_loop()
        self._restore_console = win32.enable_application_mode()
        self._writer_thread = WriterThread(self._file)
        self._writer_thread.start()
        self.write("\x1b[?1049h")
        self._enable_mouse_support()
        self.write("\x1b[?25l")
        self.write("\033[?1004h")
        self.write("\x1b[>1u")
        self.flush()
        self._enable_bracketed_paste()
        self._event_thread = _ImeEventMonitor(
            loop, self._app, self.exit_event, self.process_message
        )
        self._event_thread.start()

    def disable_input(self) -> None:
        try:
            if not self.exit_event.is_set():
                self._disable_mouse_support()
                self.exit_event.set()
                if self._event_thread is not None:
                    self._event_thread.join()
                    self._event_thread = None
                self.exit_event.clear()
        except Exception:
            pass

    def stop_application_mode(self) -> None:
        self._disable_bracketed_paste()
        self.disable_input()
        self.write("\x1b[<u")
        self.write("\x1b[?1049l" + "\x1b[?25h")
        self.write("\033[?1004l")
        self.flush()

    def close(self) -> None:
        if self._writer_thread is not None:
            self._writer_thread.stop()
        if self._restore_console:
            self._restore_console()
