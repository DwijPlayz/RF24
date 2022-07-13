"""A scanner example written in python using the std lib's ncurses wrapper"""
import curses
import time
from typing import List, Tuple, Any, Optional

from RF24 import RF24, RF24_1MBPS, RF24_2MBPS, RF24_250KBPS

CSN_PIN = 0  # connected to GPIO8
CE_PIN = 22  # connected to GPIO22
radio = RF24(CE_PIN, CSN_PIN)

if not radio.begin():
    raise RuntimeError("Radio hardware not responding!")
radio.setAutoAck(False)
radio.disableCRC()
radio.setAddressWidth(2)
radio.openReadingPipe(0, b"\x55\x55")
radio.openReadingPipe(1, b"\xAA\xAA")
radio.startListening()
radio.stopListening()
radio.flush_rx()

OFFERED_DATA_RATES = ["1 Mbps", "2 Mbps", "250 kbps"]
AVAILABLE_RATES = [RF24_1MBPS, RF24_2MBPS, RF24_250KBPS]
TOTAL_CHANNELS = 126
CACHE_MAX = 5  # the depth of history to calculate peaks
history = [[False] * CACHE_MAX] * TOTAL_CHANNELS  # FIFO for tracking peak decays
totals = [0] * TOTAL_CHANNELS  # for the total signal counts


class ProgressBar:  # pylint: disable=too-few-public-methods
    """This represents a progress bar using a curses window object."""

    def __init__(  # pylint: disable=too-many-arguments,invalid-name
        self,
        x: int,
        y: int,
        cols: int,
        std_scr: curses.window,
        label: str,
        color: curses.color_pair,
    ):
        self.x, self.y, self.width, self.win, self.color = (x, y, cols, std_scr, color)
        string = label  # always labeled in MHz (4 digits)
        # -9 for padding, label, & signal count
        string += "─" * (self.width - 8)
        string += " - "  # the initial signal count
        self.win.addstr(self.y, self.x, string, self.color)

    def update(self, completed: int, signal_count: int):
        filled = min(CACHE_MAX, completed) / CACHE_MAX
        bar = "═" * int((self.width - 8) * filled)
        empty = "─" * (self.width - 8 - len(bar))
        count = "-"
        if signal_count:
            count = "%X" % min(0xF, signal_count)
        self.win.addstr(self.y, self.x + 5, bar, curses.color_pair(5))
        self.win.addstr(self.y, self.x + 5 + len(bar), f"{empty} {count} ", self.color)


def init_interface(window) -> List[ProgressBar]:
    """Creates a table of progress bars (1 for each channel)."""
    progress_bars: List[ProgressBar] = [None] * TOTAL_CHANNELS
    bar_w = int(curses.COLS / 6)
    for i in range(21):  # 21 rows
        for j in range(i, i + (21 * 6), 21):  # 6 columns
            color = curses.color_pair(7) if int(j / 21) % 2 else curses.color_pair(3)
            progress_bars[j] = ProgressBar(
                x=bar_w * int(j / 21),
                y=i + 1,
                cols=bar_w,
                std_scr=window,
                label=f"{2400 + (j)} ",
                color=color,
            )
    return progress_bars


def init_curses():
    """init the curses interface"""
    std_scr = curses.initscr()
    # stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
    return std_scr


def deinit_curses(std_scr: curses.window, output: Optional[curses.window]):
    """de-init the curses interface"""
    # std_scr.keypad(False)
    curses.nocbreak()
    curses.echo()
    cache_out = []
    if output is not None:
        for line in range(1, 21):
            cache_out.append(output.instr(line, 0).decode())
    curses.endwin()
    print("\n".join(cache_out))


def get_user_input() -> Tuple[int, int]:
    """Get input parameters for the scan from the user."""
    for i, d_rate in enumerate(OFFERED_DATA_RATES):
        print(f"{i + 1}. {d_rate}")
    d_rate = int(input("Select your data rate [1, 2, 3] (defaults to 1 Mbps) ") or "1")
    duration = input("how long (in seconds) to perform scan? ")
    while duration is None or not duration.isdigit():
        print("Please enter a number.")
        duration = input("how long (in seconds) to perform scan? ")
    return (min(1, max(3, d_rate)) - 1, abs(int(duration)))


def scan_channel(channel: int) -> bool:
    """Scan a specified channel and report if a signal was detected."""
    radio.channel = channel
    radio.startListening()
    time.sleep(0.00013)
    result = radio.testRPD()
    radio.stopListening()
    result = result or radio.testRPD()
    if result:
        radio.flush_rx()
    return result


def main():
    data_rate, duration = get_user_input()
    radio.setDataRate(AVAILABLE_RATES[data_rate])
    scanner_output_window = None
    try:
        std_scr = init_curses()
        timer_prompt = "Scanning for {} seconds at " + OFFERED_DATA_RATES[data_rate]
        scanner_output_window = std_scr.subpad(26, curses.COLS, 0, 0)
        table = init_interface(scanner_output_window)
        channel, val = (0, False)
        end = time.monotonic() + duration
        while time.monotonic() < end:
            std_scr.addstr(0, 0, timer_prompt.format(int(end - time.monotonic())))
            val = scan_channel(channel)
            totals[channel] += val
            history[channel] = history[channel][1:] + [val]
            table[channel].update(history[channel].count(True), totals[channel])
            scanner_output_window.refresh()
            channel = 0 if channel + 1 == TOTAL_CHANNELS else channel + 1
    finally:
        radio.powerDown()
        deinit_curses(std_scr, scanner_output_window)


if __name__ == "__main__":
    main()
else:
    print("Enter 'main()' to run the program.")