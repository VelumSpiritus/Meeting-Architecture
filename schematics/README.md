# Circuit drawings: chronology and provenance

1. `crystal_circuit_complete.svg` and `crystal_circuit_v2.svg` are the earlier speaker-era drawings also represented on the [Figma board](https://www.figma.com/file/PVCwILeP1i65cee6fr8bTY?type=whiteboard). The board's build steps include a speaker, a 6 V E10 bulb, a PAM8403, a sensing piezo, and a salt-water return contact.
2. `crystal_circuit_speaker_free_reconstruction.svg` is a new *topology reconstruction* of the later measured arrangement. The [dated build excerpts](../data/build_chronology_excerpt.md) establish the speaker-lead replacement and Noah's placement of the second piezo beneath the quartz, facing the upper sensing piezo. The PAM8403 and nominal 5 V supply remained in the measured run. The sensing path was read by the DSO.
3. `crystal_circuit_self_sustaining.svg` shows a proposed inverter replacement. That configuration was not built for the photographed longitudinal series.

## Connections that still need bench confirmation

- The exact breadboard holes and module pads after the speaker was replaced.
- Whether the E10 bulb still occupied the series path in the photographed run. It is shown in the reconstruction because it was on the speaker-era output path and the instruction was to replace the speaker leads in those positions.
- Whether the salt-water return contact from v2 remained connected in the photographed run. It is dashed in the reconstruction.
- Whether any v2 jumper tied the PAM8403 left-channel negative **output** to the supply ground rail after the swap. The old drawing depicts such a route, while the [manufacturer's PAM8403 datasheet](https://www.diodes.com/datasheet/download/PAM8403.pdf) names separate `+OUT_L`, `-OUT_L`, and ground pins and shows the load across the output pair. The reconstruction keeps `L-` separate from supply ground and does not certify the bench wiring.

Solid electrical paths in the reconstruction represent the functional speaker-to-piezo swap and retained source/input/scope path. Pink dashed paths are inherited details awaiting verification. The drawing is a readable circuit account for review, not a measured netlist or a claim that each old breadboard row survived unchanged.
