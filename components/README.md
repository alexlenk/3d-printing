# Component library

Measured or researched dimensions of parts used in enclosures, so the next box doesn't start
from scratch. Each file is one part: what it is, the numbers, where every number came from,
and a ready `spec.json` snippet for the [electronics-enclosure skill](../skills/electronics-enclosure/SKILL.md).

| Part | File | Status |
|---|---|---|
| Waveshare ESP32-C3-Zero | [esp32-c3-zero.md](esp32-c3-zero.md) | printed and fitted |
| Waveshare DC5-36-TO-DC3V3-5 buck module | [waveshare-dc5-36-buck.md](waveshare-dc5-36-buck.md) | printed and fitted |
| WAGO 221-413 lever connector | [wago-221-413.md](wago-221-413.md) | printed and fitted |
| Panel DC jack 5.5/2.1, M8 | [dc-jack-5521-m8.md](dc-jack-5521-m8.md) | printed |
| Dupont / jumper housings | [dupont-housings.md](dupont-housings.md) | printed |
| USB-C cable plug | [usb-c-plug.md](usb-c-plug.md) | printed |
| Disc magnets Ø4 × 2 | [magnet-4x2.md](magnet-4x2.md) | printed (press-fit) |

## Status levels

- **printed and fitted** - a box built from these numbers was printed and the part fitted.
- **printed** - used in a printed box, but the fit-critical numbers were not separately confirmed.
- **measured** - calipers or a scaled photo of the actual part, not yet printed.
- **datasheet** - from a drawing only. Clones and revisions differ: confirm with a photo first.

## Adding a part

Copy [_template.md](_template.md) to `<maker>-<part>.md`, fill it in and add a row above.

- Every number gets a source: *measured (calipers)*, *photo estimate*, *datasheet: link*, or
  *assumed*. Assumed numbers are fine to record, but say so.
- Describe the board frame in words (which edge is x = 0, which is y = 0). Mirror mistakes
  start there.
- Record everything within ~1 mm of a PCB edge: latches grip there.
- Only public information: link product pages and datasheets instead of copying their images.
