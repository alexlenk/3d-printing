# Panel DC jack 5.5 / 2.1 mm, M8 thread

**Status:** printed (generic part - bodies vary between sellers)

| What | Value | Source |
|---|---|---|
| Panel hole | Ø8.0 (M8 thread) | common for this jack type |
| Nut | ~12.7 across corners | typical |
| Body behind the wall | Ø~11 x 14-16 mm | typical - measure yours |
| Anti-rotation flat | only some jacks have one; measure the width across the flat (e.g. 7.2) | - |
| Metal | yes | - |

Leave ~16 mm free behind the wall and keep it >= 10 mm from any antenna.

```json
{"id": "jack", "wall": "left", "u": 46.5, "z": 10.0, "cut": {"d": 8.0},
 "body": {"d": 11.0, "depth": 16.0, "nut_ac": 12.7}, "label": "12V IN"}
```
