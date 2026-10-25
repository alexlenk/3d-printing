# 3d-printing

3D-printable designs and the tooling to make new ones, mainly enclosures for electronics
projects (ESP32 & co., buck converters, WAGO connectors, sensors).

The repo is built so an AI agent (Claude Code, Claude.ai with the skill, or similar) can be
pointed at it and design a new, directly printable box: the workflow, the design rules that
have proven themselves in print, a component library with measured parts, and finished projects
as examples.

| Folder | What |
|---|---|
| [skills/electronics-enclosure](skills/electronics-enclosure/SKILL.md) | The enclosure designer: workflow (`SKILL.md`), a PythonSCAD library that builds base + snap lid from a `spec.json`, a checker (collisions, clearances, lid fit, antenna keep-out, overhangs) and a renderer. |
| [components](components/README.md) | Measured part data (ESP32-C3-Zero, buck module, WAGO, DC jack, ...), each with sources and a `spec.json` snippet. |
| [projects](projects/) | Finished designs with STLs, source and notes. |
| [tools](tools/) | Repo helpers, e.g. packaging the skill for Claude.ai. |

## Designing a new box with an agent

Point the agent at this repo and describe the electronics, e.g.:

> Read AGENTS.md in github.com/alexlenk/3d-printing and design a printable case for a
> Waveshare ESP32-C3-Zero and a DHT22 module, wall-mounted.

The agent follows [AGENTS.md](AGENTS.md): it asks for photos and any uncertain dimensions
first, proposes a layout, then builds, checks and renders the box before handing over STLs.

## Using the skill in Claude.ai

```bash
python tools/package_skill.py          # -> dist/electronics-enclosure.skill
```

Upload `dist/electronics-enclosure.skill` under Settings -> Capabilities -> Skills. The package
includes the component library.

## Running the tools locally

```bash
pip install pythonscad trimesh manifold3d shapely scipy rtree networkx pillow numpy
S=skills/electronics-enclosure/scripts
python $S/build.py  my-box/spec.json my-box/out
python $S/check.py  my-box/spec.json my-box/out
python $S/render.py my-box/spec.json my-box/out my-box/out/preview.png
```

Python 3.10-3.14. No OpenSCAD install, OpenGL or Docker needed.

## Projects

| Project | What | Status |
|---|---|---|
| [rack-fan-controller](projects/rack-fan-controller/) | ESP32-C3-Zero + buck + 2 WAGO, snap lid, magnets, for a 19" rack | printed |

## License

[MIT](LICENSE)
