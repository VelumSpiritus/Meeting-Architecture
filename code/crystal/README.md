# Crystal observations

This directory keeps photographed and measured properties separate from fitted
or assumed simulator parameters. `observations.jsonl` is append-only: each new
face or measurement adds a reading; later identification does not rewrite the
earlier visual evidence.

Face letters are handling labels only until crystallographic orientation is
independently established. A photographed plane is not assigned an electrical
axis from appearance.

`instruments.json` records the actual measurement column separately. Meter
loading is not inserted into normalized dynamics until the units joining its
ohms to the modeled capacitance have been derived.
