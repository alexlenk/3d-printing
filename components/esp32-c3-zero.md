# Waveshare ESP32-C3-Zero

**Status:** printed and fitted (pins up, Dupont plugs on top, USB-C through the wall)
**Used in:** [projects/rack-fan-controller](../projects/rack-fan-controller/)
**Links:** [Waveshare docs](https://docs.waveshare.com/ESP32-C3-Zero) ·
[schematic (PDF)](https://files.waveshare.com/wiki/ESP32-C3-Zero/ESP32-C3-Zero-Sch.pdf) ·
[footprint from Waveshare's drawing (NNTin/CanFactory#72)](https://github.com/NNTin/CanFactory/pull/72) ·
[NuttX board page (pad order)](https://nuttx.apache.org/docs/latest/platforms/risc-v/esp32c3/boards/esp32-c3-zero/index.html)

## Board frame

Component side up, USB-C pointing left. x along the length from the USB end (x = 0 = PCB edge
at the USB side), y across from the long edge with the 5V / GND / 3V3 pins.

## Dimensions

| What | Value | Source |
|---|---|---|
| PCB | 23.55 x 18.0 x 1.0, corners R1 | length measured (calipers); drawing says 23.5 |
| Header rows | y = 1.38 and 16.62, first pin x = 1.59, 9 pins each, pitch 2.54 | Waveshare drawing |
| Header plastic (2.54 strip) | x 0.32-23.18, y 0.11-2.65 / 15.35-17.89, 2.5 high | standard header |
| USB-C receptacle | overhangs the x = 0 edge by **~1.7**; 8.94 wide, ~3.2 above the PCB, ~7.6 long from its face -> box [-1.7, 4.53, 0, 5.9, 13.47, 3.2] | photo estimate - measure |
| Under the USB-C | no legs / solder stubs under the PCB | confirmed on the real board |
| Ceramic antenna | far end, **not centred**: y = 2.9-10.6 (incl. pads), within ~2.2 of the x = 23.55 edge | photo estimate, fitted |
| RGB LED (WS2812, GPIO10) | x ~8.3-10.3, y ~7.9-9.9 | drawing + photo |
| BOOT / RESET buttons | x ~8.5, y ~4.5 and ~13.2 | photo |
| Round test pads 14/15/16 | start at y ~13.9, >= 0.7 in from the end edge | photo |

## Pins

Pads are numbered anticlockwise from the USB end: 1 = 5V, 2 = GND, 3 = 3V3, then GPIO0-10 and
GPIO18-21 (NuttX page). Only **one GND** pad. Avoid for general I/O: strapping pins GPIO2/8/9,
GPIO10 (RGB LED), GPIO18/19 (USB D-/D+), GPIO20/21 (UART). The exact physical order of the GPIO
pads is not recorded here yet - use the silkscreen labels.

Power: 5V pad takes 3.7-6 V (Waveshare). Whether a diode separates USB VBUS from the 5V pad is
**not confirmed** - don't power the 5V pad and plug USB at the same time until checked.

## Where latches can grip

- Antenna end (x+ edge): free strip y = 10.9-13.9 (between the antenna and the test pads) ->
  one latch, nose 3 mm wide, centred at y = 12.4. **Not** centred on the edge.
- Long edges: no - header plastic reaches to ~0.1 mm from the edge.
- USB end: held by a wedge over the receptacle on the wall instead.

## Seat

Ledges between the header rows only (a rim would hit the header solder stubs):
USB end x 0-1.8, antenna end x 21.05-23.55, both y 3.0-15.5. Ledge height 3 mm.

## spec.json snippet

```json
{"id": "esp", "size": [23.55, 18.0, 1.0], "at": [1.7, 10.25], "rot": 0, "rim_skip": ["x-"],
 "parts": [{"name": "usb-c", "box": [-1.7, 4.53, 0, 5.9, 13.47, 3.2], "metal": true},
           {"name": "antenna", "box": [21.35, 2.9, 0, 23.55, 10.6, 1.2], "antenna": true},
           {"name": "led", "box": [8.3, 7.93, 0, 10.3, 9.93, 0.8]},
           {"name": "header1", "box": [0.32, 0.11, 0, 23.18, 2.65, 2.5]},
           {"name": "header2", "box": [0.32, 15.35, 0, 23.18, 17.89, 2.5]}],
 "rows": [{"start": [1.59, 1.38], "n": 9}, {"start": [1.59, 16.62], "n": 9}],
 "ledges": [[0, 1.8, 3.0, 15.5], [21.05, 23.55, 3.0, 15.5]],
 "latches": [{"edge": "x+", "at": 12.4, "width": 3.0}]}
```

`at` [1.7, ...] puts the USB-C face against the left wall (overhang 1.7). Pair it with a
`usb-c` opening on that wall (`align` to the board, recess and wedge on).

## Verify before printing

- USB-C overhang (1.7 is a photo estimate; it sets where the PCB sits).
- PCB length on your batch (23.5 vs 23.55).
