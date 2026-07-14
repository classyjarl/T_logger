#!/usr/bin/env python3
"""Log MAX31856 thermocouple readings from the Nano to a CSV file.

Reads lines from the serial port and writes a Time,Temperature row for each
numeric reading, timestamped with the host system clock.

No third-party packages required -- the port is configured with stdlib termios.
"""

import argparse
import csv
import os
import signal
import sys
import termios
from datetime import datetime

BAUD_CONSTANTS = {
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200,
    230400: termios.B230400,
}


def open_serial(path, baud):
    """Open the port and put it in raw 8N1 mode at the given baud rate."""
    if baud not in BAUD_CONSTANTS:
        sys.exit(f"unsupported baud {baud}; choose from {sorted(BAUD_CONSTANTS)}")

    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)

    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)

    iflag = 0                                    # no input translation, no flow control
    oflag = 0                                    # no output post-processing
    lflag = 0                                    # raw: no echo, no canonical mode
    cflag = termios.CS8 | termios.CREAD | termios.CLOCAL
    ispeed = ospeed = BAUD_CONSTANTS[baud]

    cc = list(cc)
    cc[termios.VMIN] = 0                         # read() may return with no data...
    cc[termios.VTIME] = 10                       # ...after a 1.0s timeout

    termios.tcsetattr(fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
    termios.tcflush(fd, termios.TCIFLUSH)
    return fd


def parse_reading(line):
    """Return a float if the line holds a temperature, else None.

    The sketch emits progress dots with no newline before each println, so a
    line typically arrives as '.....23.45'. Banner text is ignored.
    """
    cleaned = line.strip().lstrip(".").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-p", "--port", default="/dev/ttyUSB0")
    ap.add_argument("-b", "--baud", type=int, default=115200)
    ap.add_argument("-o", "--out", help="default: temperature_log_<date>_<time>.csv")
    ap.add_argument("-n", "--limit", type=int, help="stop after N readings")
    args = ap.parse_args()

    started = datetime.now()
    out_path = args.out or f"temperature_log_{started:%Y-%m-%d_%H-%M-%S}.csv"

    fd = open_serial(args.port, args.baud)

    # Opening the port resets the Nano (DTR), so the sketch restarts and we see
    # its banner before any readings arrive.
    print(f"listening on {args.port} at {args.baud}; writing {out_path}  (Ctrl-C to stop)")
    print(f"started {started:%Y-%m-%d %H:%M:%S %Z}".rstrip())

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    count = 0
    buf = b""
    try:
        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "Temperature"])

            while True:
                chunk = os.read(fd, 256)
                if not chunk:
                    continue                     # VTIME timeout, board just idle
                buf += chunk

                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode("utf-8", errors="replace")

                    temp = parse_reading(line)
                    if temp is None:
                        text = line.strip()
                        if text.strip("."):      # surface banner/error text, not dots
                            print(f"  [board] {text}")
                        continue

                    # Local time-of-day; the calendar date lives in the filename.
                    now = datetime.now()
                    stamp = f"{now:%H:%M:%S}.{now.microsecond // 1000:03d}"
                    writer.writerow([stamp, f"{temp:.2f}"])
                    f.flush()                    # survive Ctrl-C with data intact
                    os.fsync(f.fileno())

                    count += 1
                    print(f"  {stamp}  {temp:.2f}")

                    if args.limit and count >= args.limit:
                        return
    finally:
        os.close(fd)
        print(f"\nwrote {count} readings to {out_path}")


if __name__ == "__main__":
    main()
