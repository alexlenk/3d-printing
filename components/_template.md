# <Maker> <Part name>

**Status:** measured | datasheet | printed | printed and fitted
**Used in:** projects/... (if any)
**Links:** product page, datasheet / drawing

## Board frame

Which edge is x = 0, which is y = 0, component side up (e.g. "x along the length from the USB
end, y from the edge with the 5V / GND / 3V3 pins").

## Dimensions

| What | Value | Source |
|---|---|---|
| PCB L x W x T | | |
| Tallest part above the PCB | | |
| Connectors (position, overhang past the PCB edge) | | |
| Pins / holes (first pin, pitch, rows) | | |
| Parts within 1 mm of an edge | | |
| Underside (solder stubs, legs) | | |
| Antenna / keep-out | | |

## Where latches can grip

Free edge strips (>= 1 mm of bare PCB at the edge, nothing within 1 mm).

## spec.json snippet

```json
{"id": "...", "size": [0, 0, 0], "parts": [], "pins": [], "ledges": [], "latches": []}
```

## Verify before printing

What hasn't been confirmed on a real part yet.
