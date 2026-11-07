# Voice-Controlled CNC Writing Machine

An offline, voice-controlled computer numerical control (CNC) writing and drawing machine that physically plots spoken input onto paper in real time.

---

## 🎯 System Overview
Traditional voice-enabled devices rely on constant cloud API connectivity, introducing latency and privacy risks. This project implements an **entirely offline voice-to-motion pipeline**:
1. Spoken input is captured via microphone and processed locally using the lightweight **Vosk offline speech recognition engine** on a **Raspberry Pi**.
2. Recognized text is parsed and converted into G-code toolpaths corresponding to stroke sequences for each character.
3. The Raspberry Pi streams motion commands over a USB-serial bridge to an **Arduino Uno** running Grbl firmware.
4. The Arduino controls stepper motors via a **CNC Shield** to actuate the X-Y drawing gantry and Z-axis pen lift.

---

## 🏗️ Hardware Architecture
- **Single-Board Computer:** Raspberry Pi (Speech recognition, text-to-Gcode parsing)
- **Microcontroller:** Arduino Uno (Grbl G-code interpreter & pulse generator)
- **Motor Control:** CNC Shield v3 with A4988 Stepper Drivers
- **Actuation:** NEMA 17 Stepper Motors (X & Y axes) + Micro Servo (Z-axis pen up/down)
- **Microphone:** USB Condenser Microphone
- **Power Supply:** 12V 5A DC power supply for stepper rails

---

## 💻 Software & Pipeline
- **Speech Engine:** Python + Vosk Offline STT Model
- **Serial Protocol:** PySerial (`/dev/ttyACM0` @ 115200 baud)
- **Firmware:** Grbl v1.1
- **Operating Environment:** Raspberry Pi OS (headless with terminal access)

---

## 🚀 How It Works
1. User speaks into the microphone connected to the Raspberry Pi.
2. The Vosk engine performs local acoustic-model inference on the `.wav` audio stream.
3. The parsed text string maps each letter to predefined vector stroke coordinates.
4. G-code commands (`G00`, `G01`, `M03`, `M05`) are streamed line-by-line to the Arduino.
5. The pen traces the letters onto paper with sub-millimeter precision.
