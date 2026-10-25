# Dupont / jumper-wire housings (2.54 mm)

**Status:** printed (headroom rule held up in a printed box)

| What | Value |
|---|---|
| Housing per position | 2.54 x 2.54, ~14 mm tall |
| Seated height | bottom ~3.5 mm above the PCB on standard headers |
| Wire bend room above | ~10 mm |
| Headroom to plan above a PCB with plugs on top | **28 mm** |
| Multi-pin housings | n x 2.54 wide (3-pin ~7.6 mm) |
| 4-pin fan plug (KK 254 style) | ~10.5 x 5 |

Cable openings that must pass a plug: 4-pin fan plug -> 12 x 6 slot; a Ø6 round hole passes
single housings, not a 3-pin housing.

Skill default: `"plug": {"seat": 3.5, "height": 14.0, "w": 2.54}`, `"headroom": 28.0`.
