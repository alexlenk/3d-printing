# Design rules (with the reasons)

Target: FDM, 0.4 mm nozzle, 0.2 mm layers, PETG or ASA, **no supports**, base printed
bottom-down, lid printed outer-face-down.

## Printability
- Overhangs <= 45°, bridges <= 10 mm (checker measures the distance of every downward face to
  support). Rectangular windows get 45° chamfered top corners; round wall holes get a teardrop
  top; small horizontal catches (latch noses, 0.6-0.9 mm) are fine.
- Edges on the bed get a 0.8 mm 45° chamfer (no elephant foot), vertical edges r = 2 mm.
- Minimum wall 0.8 mm (2 perimeters) only where it buys something (USB recess); default 2 mm.
- Text: bold sans, 3.5 mm cap height -> ~0.5 mm stems, printable as raised 0.6 mm relief on a
  vertical wall. Smaller text turns to mush. Raised text on a face that lies on the bed is
  impossible - put lid text engraved, or skip it.
- Every exported part must be one watertight body. Overlap joined solids by >= 0.5 mm.
- Print orientation is reached by **rotation only**. A mirror swaps sides and the part no
  longer fits (it happened). `lid_print()` rotates 180° about X; the checker verifies it.

## Fit
- Clearance 0.25 mm per side for pockets and the lid lip; 0.45 mm for loose blocks in cradles.
- Lid: 3 mm locating lip inside the walls, interrupted around snap arms.

## Board seats
- PCB rests on **ledge segments** 3 mm above the floor (room for solder stubs / pin ends).
  Put ledges where nothing is soldered: between header rows, away from connector legs.
  A rim all around the PCB would sit right under the header pins of most modules.
- Rim around the pocket (1.2 mm) with its top flush with the PCB top: locates the board and
  gives a flat surface for a dab of hot glue on plugs/cables. No rim on an edge against a wall.
- **Spring latch** (what holds the board): plate 1.2 mm thick, 9 mm free length, standing in a
  slot cut through the floor so it can flex sideways; nose reaches 0.6 mm over the PCB edge,
  45° lead-in on top, flat catch below. Strain = 1.5 * t * deflection / L^2 ~ 2 % (PETG/ASA
  tolerate ~3-4 % for repeated snaps). A vertical hook rising from the floor is only ~4 mm long
  and strains ~5 % - it cracks. Place the nose where the PCB edge is bare for >= 1 mm
  (no part within 1 mm of the edge, not over an antenna). One latch on the edge opposite a
  wall-held connector is enough for small boards; two (on opposite long sides) for longer
  modules.
- Release: push the latch plate outwards with a small screwdriver.

## USB-C
- Receptacle face against the inner wall. If it overhangs the PCB (common on small dev boards,
  ~1.5-2 mm), the board sits back by that amount - measure it.
- Cutout 10 x 4.5 mm (shell 8.3 x 2.6), plus an outside recess 13 x 7.5 mm leaving 0.8 mm wall:
  cable overmolds then stop 0.8 mm before the receptacle and the plug engages ~5.8 of 6.6 mm.
  Without the recess (2 mm wall) engagement drops to ~4.6 mm and some cables won't latch.
- Wedge on the inside of the wall over the receptacle (45° underside) keeps that end down.
- Insert the board USB-end first under the wedge, then press the far end down onto the latch.

## Wall openings and labels
- Cable slot for a connector that must pass: size it to the plug housing (4-pin fan plug
  ~10.5 x 5 -> 12 x 6 slot). Round Ø6 passes single Dupont housings, not multi-pin housings.
- Panel DC jack 5.5/2.1 with M8 thread: Ø8.0 hole; leave ~16 mm free behind the wall; a D-flat
  only if the jack really has a flat.
- Every opening gets a label (raised) placed above it by default; labels must stay >= 1 mm from
  openings, vents, windows and wall edges (checked; labels slide automatically).
- Vent slots 1.5 mm wide (finger-safe, coarse dust), pitch 3, near the heat source, on two
  opposite walls for through-flow. Keep >= 3 mm solid wall to any catch window.

## Snap lid (screwless)
- 4 arms 8 x 1.6 mm, 11 mm long, hanging from the lid; nose reaches 0.9 mm into a 9 x 3.3 mm
  window near the top of the wall. 30° lead-in (presses on with ~12 N/arm), 45° catch
  (~20 N/arm to pull off), strain ~1.8 %. Release: push each nose in through its window.
- **Symmetric**: arms at the same positions on opposite walls, mirrored about the centre, so
  the lid fits both ways round. Arms may hang into a board's free zone only above the top of
  its plugs (checked).
- The catch faces print at exactly 45° when the lid lies face-down.

## Layout (assembly friendliness)
- Spread parts over the whole floor; the checker lists edge-to-edge gaps and the largest empty
  circle - if two parts are a few mm apart while a 30 mm hole stays empty, move them.
- Cable entries near where those wires terminate and with free floor behind them; not inside a
  board's 10 mm plug field. A zip-tie anchor on the floor behind every cable entry.
- Antenna >= 10 mm from metal; heat sources next to vents; panel parts away from board plug fields.
- Symmetry: snaps, magnets (4 corners), tabs (centred) unless something forces otherwise - and
  then say why.

## Mounting
- Magnets Ø4 x 2: press-fit hole Ø4.1 x 2.0 from the bottom, flush; inside a Ø8 x 1.2 boss so
  1.2 mm plastic remains above. Four, one per corner.
- Screw tabs flush with the bottom, 4 mm thick, Ø4.5 hole, clipped at the wall (nothing may
  reach into the box).
