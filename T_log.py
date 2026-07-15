import serial, serial.tools.list_ports
import csv, datetime

def find_arduino():
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "") + (p.manufacturer or "")
        if any(k in desc for k in ("Arduino", "CH340")):
            venid = hex(int(p.vid))
            print(venid)
            print(p.description)
            return p.device
        # Common Arduino/clone VIDs: 0x2341 (Arduino), 0x1A86 (CH340), 0x0403 (FTDI)
        if p.vid in (0x2341, 0x1A86) and p.vid is not (0x0403):
            return p.device
        
    return None

def name_file(analyte: str) -> str:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")  # no colons
    return f"{analyte}_{stamp}"
def get_time():
    Hour = datetime.datetime.now().hour
    Minute = datetime.datetime.now().minute
    Second = datetime.datetime.now().second
    Usecond = datetime.datetime.now().microsecond
    name = [Hour, Minute, Second, Usecond]
    Time = f"{name[0]}:{name[1]}:{name[2]}:{name[3]}"
    return Time

port = find_arduino()
if not port:
    raise SystemExit("No Arduino found")
print("Using", port)

ser = serial.Serial(port, 115200, timeout=1)   # timeout so readline() returns

analyte = "n-hexane"
fname = name_file(analyte) + ".csv"

with open(fname, "a", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Time", "Temperature"])       # list, not a string
    print(f"Logging to {fname} — Ctrl-C to stop")
    try:
        while True:
            line = ser.readline().decode(errors="replace").strip()
            if not line:                       # timeout gave empty string, no data
                continue
            w.writerow([get_time(), line])
            f.flush()                          # data hits disk each row
            print("Time:",get_time(),"T:",line, "K")
    except KeyboardInterrupt:
        print(f"\nStopped. Saved to {fname}")
    finally:
        ser.close()