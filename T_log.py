import serial
import serial, serial.tools.list_ports
import csv, datetime

def find_arduino():
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "") + (p.manufacturer or "")
        if any(k in desc for k in ("Arduino", "CH340", "FTDI", "USB Serial", "USB-SERIAL")):
            return p.device
        # Common Arduino/clone VIDs: 0x2341 (Arduino), 0x1A86 (CH340), 0x0403 (FTDI)
        if p.vid in (0x2341, 0x1A86, 0x0403):
            return p.device
    return None

port = find_arduino()
if not port:
    raise SystemExit("No Arduino found")
print("Using", port)

ser = serial.Serial(port, 9600)

def Name_File(analyte: str) -> str:
    
    Tdate = str(datetime.date.today())
    Ctime = str(datetime.time.isoformat())
    Fname = analyte +"_"+ Tdate + Ctime
    return Fname

analyte = "n-hexane"
fname = Name_File(analyte)
with open(fname + ".csv", "a",newline="") as f:
    w = csv.writer(f)
    w.writerow("Time, Temperature")
    while True:
            line = ser.readline().decode(errors="replace").strip()
            w.writerow([datetime.datetime.now().isoformat(), line])
            print(line)