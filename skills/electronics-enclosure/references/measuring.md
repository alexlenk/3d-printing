# Getting dimensions from photos

Most users can send a product photo or a phone picture faster than they can measure ten
positions. A straight-on top view is enough for positions in the board plane to ~0.3 mm.

1. Find the PCB outline in pixels (left/right/top/bottom edge). Scale = known PCB size (mm)
   / outline size (px); check that the scale is the same in both directions (if not, the photo
   is skewed - ask for a straighter one or use the average and flag it).
2. Decide the board frame (which edge is x = 0, which is y = 0) and say it in words in the spec
   (e.g. "y from the 5V/GND/3V3 edge"). Mirror mistakes start here.
3. For every feature near an edge (connectors, antennas, capacitors, test pads, mounting
   holes), record its box in mm. Anything within ~1 mm of an edge matters for latches.
4. Connectors that overhang the PCB edge (USB-C on small boards!) - measure the overhang.
5. Heights cannot come from a top photo: ask, or use datasheet values, and flag them.
6. Cross-check with datasheet drawings where available (pin pitch 2.54, row offsets).

Write every photo-derived number into the verify-before-printing list, with what to measure.
If the user can measure with calipers, ask for: PCB length/width/thickness, connector
overhang, height of the tallest part, and the distance of the first pin from the edge.
