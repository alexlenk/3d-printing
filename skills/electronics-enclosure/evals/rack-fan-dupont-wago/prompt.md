---
tags: [electronics-enclosure]
max_turns: 120
timeout_seconds: 5400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I need a 3D-printed box for my ESPHome rack fan controller. Inside: a Waveshare ESP32-C3-Zero (headers soldered, pins pointing up, Dupont plugs on top), a Waveshare DC5-36-TO-DC3V3-5 buck module (12V -> 5V, pins up too), and 2 WAGO 221-413 connectors (12V and GND). Outside: a 5.5/2.1 panel DC jack for 12V in, a 4-pin PWM fan cable and a 3-wire DHT22 cable go out of the box. It hangs on a 19" network rack, so 4 small 4x2 mm magnets in the bottom please, plus two screw tabs. Lid without screws. Labels next to the openings (USB, 12V IN, FAN, SENSOR). PETG, 0.4 nozzle.

I measured the ESP PCB: 23.55 mm long. From the photos: the USB-C sticks out about 1.7 mm past the PCB edge, the ceramic antenna is at the other end, offset to one side (2.9-10.6 mm from the 5V/GND/3V3 edge). The buck module has 4 VIN holes (about 3.5 mm pitch) at one end and 6 output pins at the other; two output capacitors sit 0.4 mm from one long edge between 19 and 30 mm from the VIN end.
