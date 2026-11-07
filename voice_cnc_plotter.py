#!/usr/bin/env python3
"""
Voice-Controlled CNC Plotter
Offline
Raspberry Pi
VOSK
GRBL compatible
No wake word
Manual start
Early stop with ENTER
Time progress shown
Recognized words printed
"""

import sys
import time
import json
import queue
import select
import glob
import subprocess
import serial
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# ================= CONFIG =================
DRY_RUN = False
BAUD_RATE = 115200
MAX_RECORD_SECONDS = 120

AUDIO_DEVICE_INDEX = 1
VOSK_MODEL_PATH = "/home/pi/vosk-model-small-en-us-0.15"

A4_WIDTH = 210
A4_HEIGHT = 297
MARGIN = 10

CHAR_WIDTH = 12
CHAR_HEIGHT = 10
SCALE = 0.6
START_X = 10
START_Y = 20
def initialize_machine(ser):
    print("Initializing machine...")

    ser.write(b"$X\n")
    time.sleep(0.5)

    ser.write(b"$H\n")

    # Wait for homing to complete
    while True:
        line = ser.readline().decode().strip()
        if line:
            print("GRBL:", line)
        if line == "ok":
            break

    ser.write(b"G90\n")
    ser.write(b"G21\n")

    ser.write(b"G0 X10 Y270\n")

    print("Machine ready.")
# =========================================

def get_supported_samplerate(device):
    for rate in (48000, 44100, 16000):
        try:
            sd.check_input_settings(
                device=device,
                samplerate=rate,
                channels=1,
                dtype="int16"
            )
            return rate
        except Exception:
            pass
    raise RuntimeError("No supported sample rate")

# ================= FONT ===================
HERSHEY_FONT = {
    'A': [[(0,0),(5,10),(10,0)],[(2,5),(8,5)]],
    'B': [[(0,0),(0,10),(7,10),(7,5),(0,5)],[(0,5),(7,5),(7,0),(0,0)]],
    'C': [[(10,2),(8,0),(2,0),(0,2),(0,8),(2,10),(8,10),(10,8)]],
    'D': [[(0,0),(0,10),(5,10),(7,8),(7,2),(5,0),(0,0)]],
    'E': [[(10,0),(0,0),(0,10),(10,10)],[(0,5),(7,5)]],
    'F': [[(0,0),(0,10),(10,10)],[(0,5),(7,5)]],
    'G': [[(10,2),(8,0),(2,0),(0,2),(0,8),(2,10),(8,10),(10,8),(10,5),(5,5)]],
    'H': [[(0,0),(0,10)],[(10,0),(10,10)],[(0,5),(10,5)]],
    'I': [[(5,0),(5,10)],[(2,0),(8,0)],[(2,10),(8,10)]],
    'J': [[(10,10),(10,2),(8,0),(2,0),(0,2)]],
    'K': [[(0,0),(0,10)],[(10,10),(0,5),(10,0)]],
    'L': [[(0,10),(0,0),(10,0)]],
    'M': [[(0,0),(0,10),(5,5),(10,10),(10,0)]],
    'N': [[(0,0),(0,10),(10,0),(10,10)]],
    'O': [[(2,0),(8,0),(10,2),(10,8),(8,10),(2,10),(0,8),(0,2),(2,0)]],
    'P': [[(0,0),(0,10),(7,10),(10,8),(10,6),(7,5),(0,5)]],
    'Q': [[(2,0),(8,0),(10,2),(10,8),(8,10),(2,10),(0,8),(0,2),(2,0)],[(6,4),(10,0)]],
    'R': [[(0,0),(0,10),(7,10),(10,8),(10,6),(7,5),(0,5)],[(5,5),(10,0)]],
    'S': [[(10,8),(8,10),(2,10),(0,8),(2,6),(8,4),(10,2),(8,0),(2,0),(0,2)]],
    'T': [[(0,10),(10,10)],[(5,10),(5,0)]],
    'U': [[(0,10),(0,2),(2,0),(8,0),(10,2),(10,10)]],
    'V': [[(0,10),(5,0),(10,10)]],
    'W': [[(0,10),(2,0),(5,5),(8,0),(10,10)]],
    'X': [[(0,0),(10,10)],[(10,0),(0,10)]],
    'Y': [[(0,10),(5,5),(10,10)],[(5,5),(5,0)]],
    'Z': [[(0,10),(10,10),(0,0),(10,0)]],
    '0': [[(2,0),(8,0),(10,2),(10,8),(8,10),(2,10),(0,8),(0,2),(2,0)]],
    '1': [[(5,0),(5,10)]],
    '2': [[(0,8),(2,10),(8,10),(10,8),(10,6),(0,0),(10,0)]],
    '3': [[(0,10),(10,10),(10,5),(0,5)],[(10,5),(10,0),(0,0)]],
    '4': [[(7,10),(0,3),(10,3)],[(7,10),(7,0)]],
    '5': [[(10,10),(0,10),(0,5),(10,5),(10,0),(0,0)]],
    '6': [[(8,10),(2,10),(0,8),(0,2),(2,0),(8,0),(10,2),(10,4),(8,5),(2,5)]],
    '7': [[(0,10),(10,10),(5,0)]],
    '8': [[(2,5),(0,6),(0,8),(2,10),(8,10),(10,8),(10,6),(8,5),
            (2,5),(0,4),(0,2),(2,0),(8,0),(10,2),(10,4),(8,5)]],
    '9': [[(10,6),(8,5),(2,5),(0,6),(0,8),(2,10),(8,10),(10,8),(10,2),(8,0),(2,0)]],
    ' ': []
}
# =========================================

def find_arduino():
    ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    return ports[0] if ports else None

def beep():
    subprocess.run(
        ["aplay", "beep.wav"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def clamp(val, lo, hi):
    return max(lo, min(val, hi))

def init_grbl(ser):
    ser.write(b"\r\n\r\n")
    time.sleep(2)
    ser.flushInput()
    print("GRBL ready")

def send_grbl_line(ser, line):
    print(">>", line)
    ser.write((line + "\n").encode())
    while True:
        resp = ser.readline().decode().strip()
        if resp == "ok":
            return
        if "error" in resp:
            print("GRBL ERROR:", resp)
            return

class VoiceCNC:
    def __init__(self):
        print("Loading VOSK model")
        self.model = Model(VOSK_MODEL_PATH)
        self.sample_rate = get_supported_samplerate(AUDIO_DEVICE_INDEX)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.audio_q = queue.Queue()

        self.serial = None
        if not DRY_RUN:
            port = find_arduino()
            if not port:
                print("Arduino not found")
                sys.exit(1)
            self.serial = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(2)   # wait for Arduino reset
            initialize_machine(self.serial)
            init_grbl(self.serial)
        else:
            print("DRY RUN enabled")

    def audio_callback(self, indata, frames, time_info, status):
        self.audio_q.put(bytes(indata))

    def listen(self):
        self.recognizer.Reset()
        with self.audio_q.mutex:
            self.audio_q.queue.clear()

        print("Enter recording duration in seconds")
        try:
            duration = int(input("> ").strip())
        except ValueError:
            duration = 10

        duration = min(duration, MAX_RECORD_SECONDS)

        print("Press ENTER to start recording")
        input()
        beep()

        print("Recording started")
        print("Press ENTER to stop early")

        with sd.RawInputStream(
            device=AUDIO_DEVICE_INDEX,
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self.audio_callback
        ):
            start = time.time()
            last_sec = -1

            while True:
                elapsed = int(time.time() - start)

                if elapsed != last_sec and elapsed <= duration:
                    print(f"{elapsed}/{duration} sec")
                    last_sec = elapsed

                if elapsed >= duration:
                    break

                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    input()
                    break

                try:
                    data = self.audio_q.get(timeout=0.1)
                    self.recognizer.AcceptWaveform(data)
                except queue.Empty:
                    pass

        beep()
        result = json.loads(self.recognizer.FinalResult())
        text = result.get("text", "").strip()
        print("Recognized:", text if text else "(nothing)")
        return text

    def text_to_gcode(self, text):
        gcode = ["G21", "G90", "F1000", "M5"]
        x, y = START_X, START_Y

        for ch in text.upper():
            if ch not in HERSHEY_FONT:
                x += CHAR_WIDTH * SCALE
                continue

            for stroke in HERSHEY_FONT[ch]:
                sx = stroke[0][0] * SCALE
                sy = stroke[0][1] * SCALE
                gcode.append(f"G0 X{x+sx} Y{y+sy}")
                gcode.append("M3")


                for px, py in stroke[1:]:
                    gx = clamp(x + px*SCALE, MARGIN, A4_WIDTH - MARGIN)
                    gy = clamp(y + py*SCALE, MARGIN, A4_HEIGHT - MARGIN)
                    gcode.append(f"G1 X{gx} Y{gy}")

                gcode.append("M5S90")

            x += CHAR_WIDTH * SCALE

        return gcode

    def run(self):
        while True:
            text = self.listen()
            if not text:
                continue

            gcode = self.text_to_gcode(text)
            for line in gcode:
                if DRY_RUN:
                    print(line)
                else:
                    send_grbl_line(self.serial, line)

if __name__ == "__main__":
    VoiceCNC().run()
