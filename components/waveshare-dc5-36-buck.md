# Waveshare DC5-36-TO-DC3V3-5 (buck converter, 5-36 V -> 5 V or 3.3 V)

**Status:** printed and fitted (pins up, Dupont plugs on top)
**Used in:** [projects/rack-fan-controller](../projects/rack-fan-controller/)
**Links:** [Waveshare wiki](https://www.waveshare.com/wiki/DC5-36-TO-DC3V3-5) ·
[product page](https://www.waveshare.com/dc5-36-to-dc3v3-5.htm)

## Electrical (from Waveshare)

- 5 V output by default (input 6-36 V); 3.3 V mode by moving a 0R resistor (input 5-36 V).
- 0-4 A (up to 5 A briefly); add cooling above 3 A.
- Input end: VIN+ / VIN-. Output end: 3x VOUT+ and 3x GND.
- Non-isolated: input and output ground should be one net (check continuity before relying on it).
- A "-M" variant comes with headers and a screw terminal pre-soldered - different heights.

## Board frame

Component side up, VIN end on the left. x along the length from the VIN end, y across from the
long edge that has the two output capacitors close to it.

## Dimensions

| What | Value | Source |
|---|---|---|
| PCB | 33 x 16 x ~1.6 | size from Waveshare, thickness assumed |
| Module height | 5.7 | Waveshare |
| VIN holes | 4 castellated holes at x = 3.5, ~3.5 pitch; y = 3.1 / 6.6 / 10.0 / 13.5 (a second reading gave 2.5 / 6.0 / 9.4 / 12.9) | photo estimate, +-0.6 |
| Output pins | 6 at 2.54 pitch, x = 31.6, y = 1.6 ... 14.3 | photo estimate |
| Output capacitors | x = 19-30, y = 0.4-2.4, ~1.2 high - **0.4 mm from the edge** | photo |
| Inductor | ~1 mm from both long edges, x = 19-30 | photo |
| Diode | ~1 mm from the far long edge, x = 9.6-16.4 | photo |
| Component envelope | [5.5, 1.0, 0, 30.0, 15.0, 4.1] | photo + height |

## Where latches can grip

Both long edges at x ~13-17 -> two latches at x = 15, width 3.5 (one per long edge). The diode
on the far edge sits ~1 mm in, which is clear of a 0.6 mm nose.

## Seat

Ledges along both long sides, clear of the pin ends: x 4-29, y 0-1.2 and 14.8-16.

## spec.json snippet

```json
{"id": "buck", "size": [33.0, 16.0, 1.6], "at": [58.35, 46.0], "rot": 270,
 "parts": [{"name": "components", "box": [5.5, 1.0, 0, 30.0, 15.0, 4.1]},
           {"name": "edge caps", "box": [19.0, 0.4, 0, 30.0, 2.4, 1.2]}],
 "pins": [{"at": [3.5, 13.5], "d": 2.0}, {"at": [3.5, 10.0], "d": 2.0},
          {"at": [3.5, 6.6], "d": 2.0}, {"at": [3.5, 3.1], "d": 2.0}],
 "rows": [{"start": [31.6, 14.4], "dir": [0, -1], "n": 6}],
 "ledges": [[4, 29, 0, 1.2], [4, 29, 14.8, 16]],
 "latches": [{"edge": "y-", "at": 15.0, "width": 3.5}, {"edge": "y+", "at": 15.0, "width": 3.5}]}
```

Put it next to vent slots (it gets warm) and >= 10 mm from any antenna.

## Verify before printing

- PCB thickness (1.6 assumed).
- VIN hole positions (two photo readings differ by 0.6 mm; Dupont housings on 3.5 mm pitch fit
  either way, but check your header fits the holes).
