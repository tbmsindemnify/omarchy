# Voxtype DNA visualizer

The native GTK/Cairo popup cycles through chromatic DNA, 3D spiral, molecular,
blueprint, neon, wireframe, isometric, particles, liquid and holographic styles.
It keeps the configured popup size, click-through behavior, active-monitor
placement, audio socket and peak meter.

## Speech response

Relative audio-envelope onsets estimate speech cadence. Faster pulse cadence
smoothly increases rotation and tightens the artistic helices; pauses release
the compression. This is an acoustic approximation, not measured words per
minute or speech recognition. Loudness alone does not imply fast dictation.

After at least 0.7 seconds of voiced activity, a 650 ms pause can start a
1.2-second crossfade. At least two seconds separate transition starts. A short
breath does not advance the sequence. Ending a phrase and starting another
recording also advances it. Hidden time does not skip styles or render frames.
The sequence remains in memory for the lifetime of the popup process.

## Molecular provenance

`src/dna_1bna.pdb` is the RCSB PDB 1BNA X-ray structure, downloaded from
https://files.rcsb.org/download/1BNA.pdb on 2026-10-10.

- Structure: https://www.rcsb.org/structure/1BNA
- Publication: https://doi.org/10.1073/pnas.78.4.2179
- Download SHA-256: df42f1506792f191b957227b061360652adcf6f813eb69d9ec553067ea584670
- 486 DNA heavy atoms; crystal waters are excluded.

Principal-axis alignment is a rigid transform of the deposited atom positions.
Rotation and uniform display scaling preserve the molecular geometry. Element
colors, lighting, sphere radii and camera motion are artistic. Display sticks
are inferred from covalent distances within residues and O3'-P backbone links;
they are not a full chemical bond-order model. No molecular dynamics, hydrogen
atoms or simulated thermal motion are claimed. A 56-pixel popup necessarily
shows less atom detail than a taller popup.

## Verification

Run `cargo test --locked --bin voxtype` for cadence, pause transitions, geometry,
rendering and voice-response tests. `cargo run --locked --example helix_render
-- /tmp/helix-renders` exports every style at 360x56 and 480x100.

The inherited library-wide tests currently need separate repairs: the manifest
omits the `tempfile` test dependency, and old theme tests call `set_var` without
Rust 2024's required unsafe handling. These unrelated tests are not modified.
