# Design and Development of an Offline Voice-Assisted CNC Plotter Machine

An offline, speech-driven computer numerical control (CNC) plotting machine capable of transcribing spoken natural language and printing physical text onto paper without requiring any internet connection or cloud APIs.

---

## 🎯 Abstract & Motivation
Traditional voice-enabled devices rely heavily on cloud automatic speech recognition (ASR) APIs, introducing latency bottlenecks (3–6s), network dependency, and potential data privacy risks. 

This project implements an **entirely self-contained, low-latency offline hardware-software pipeline**:
1. Spoken audio is captured locally and transcribed in real time using the **VOSK offline speech recognition engine** on a **Raspberry Pi 4**.
2. Transcribed text is parsed and converted into G-code toolpaths via a custom Python algorithm utilizing a **Hershey vector stroke font** coordinate dictionary.
3. G-code instructions are streamed over a USB-serial interface (115200 baud) to an **Arduino Uno** running **GRBL firmware**, driving dual-axis stepper motors and a pen-actuating servo mechanism with high precision.

---

## 📊 Key Experimental Results & Performance Metrics

| Metric | Measured Value | Benchmark / Details |
| :--- | :--- | :--- |
| **Speech Recognition Accuracy** | **90% – 95%** | Word-error rate tested in indoor acoustic environments (VOSK v0.3.45 Kaldi acoustic model). |
| **End-to-End Latency** | **2.6s average** (2.2s – 3.0s) | Mean STT time: 2.1s ± 0.3s; G-code generation: <50ms; Serial communication: 0.2–0.5s. Outperforms typical cloud ASR latency (3–6s). |
| **Positional Precision** | **±0.08 mm** | Repeatable mechanical accuracy at 5 steps/mm (0.2 mm/step) across X and Y axes. |
| **Print Success Rate** | **100%** | Validated across multi-word phrases and the full 26-letter pangram (*"The quick brown fox jumps over the lazy dog"*). |
| **Motion Velocities** | **3000 mm/min (G00)** | Pen-up rapid positioning; 1500 mm/min (G01) linear interpolation pen-down drawing speed. |

---

## 🏗️ System Architecture

```text
[ Spoken Input / Microphone ]
              │
              ▼ (16kHz Mono Audio Stream)
┌─────────────────────────────────────────────────────────────┐
│ Raspberry Pi 4 Model B (4 GB RAM)                           │
│  ├── 1. VOSK Offline STT Engine (Kaldi Acoustic Model)      │
│  ├── 2. Command & Punctuation Parser ('full stop' -> '.')   │
│  └── 3. Text-to-GCode Generator (Hershey Vector Font Engine)│
└─────────────────────────────┬───────────────────────────────┘
                              │ (Serial USB / PySerial @ 115200 Baud)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Arduino Uno (GRBL v0.9 Firmware)                            │
│  ├── Motion Planning & Step Pulse Generation                │
│  └── Direction & Limit Switch Monitoring                    │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│ CNC Shield v3 + A4988 Drivers│ │ MG90S Micro Servo          │
│  ├── NEMA 17 Stepper (X-Axis)│ │  └── Z-Axis Pen Lift/Drop  │
│  └── NEMA 17 Stepper (Y-Axis)│ │      (M3: Down, M5 S90: Up) │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## 💻 Software Pipeline (`voice_cnc_plotter.py`)
1. **Audio Acquisition:** Audio stream captured at 16kHz mono using `sounddevice`.
2. **Offline Speech Recognition:** VOSK Kaldi model processes audio frames locally without network latency.
3. **Punctuation & Character Normalization:** Keyword substitutions replace spoken phrases (`"full stop"`, `"comma"`, `"question mark"`) with their respective punctuation symbols.
4. **Vector Stroke Mapping:** Characters are mapped to normalized `(x, y)` coordinate vectors extracted from the Hershey font dictionary and scaled to machine coordinates (`SCALE = 0.85`, `CHAR_WIDTH = 10mm`, `LINE_HEIGHT = 12.5mm`).
5. **Machine Boundary Validation:** Strictly enforces usable drawing area boundaries (A4 limits: `X=10-225mm`, `Y=10-165mm`) to prevent gantry over-travel.
6. **Streaming & Handshake:** Streams G-code line-by-line over PySerial, awaiting GRBL `ok` confirmation acknowledgments.

---

## ⚙️ Getting Started

### Prerequisites
- Raspberry Pi OS (Bullseye or Bookworm)
- Python 3.8+
- Arduino Uno with GRBL v0.9+ installed
- CNC Shield v3 with A4988 drivers & NEMA 17 steppers

### Python Dependencies
```bash
pip install vosk sounddevice pyserial
```

### Download Offline VOSK Model
```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### Run
```bash
python voice_cnc_plotter.py
```
