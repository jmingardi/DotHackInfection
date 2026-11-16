"""Replay the inspected opening through Orca's field tutorial from a fresh boot."""
import importlib.util
import json
import project

spec = importlib.util.spec_from_file_location("upstream_play", project.FW / "scripts/play.py")
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)

route = json.loads((project.ROOT / "qa/opening-route.json").read_text())
presses, axes = [], []
end = 0
for step in route:
    if step["start"] != end or step["end"] <= end:
        raise ValueError("Opening route must be contiguous")
    args = upstream.parse_moves(step["moves"], step["start"])
    for index in range(0, len(args), 2):
        (presses if args[index] == "--press" else axes).append(args[index + 1])
    end = step["end"]

project.qa(end + 1, presses, axes=axes)
