# Voxtype DNA visualizer

The native GTK/Cairo popup cycles through ten Three.js-rendered 3D designs.
Full names, descriptions, materials, depth cues and motion intent are defined
in `web/styles.json` and presented in the interactive Depth Studio preview.
It keeps the configured popup size, click-through behavior, active-monitor
placement, audio socket and peak meter.

Every design uses the same centered horizontal strand envelope and margins.
The envelope responds identically to energy and cadence in every mode; only
the rendering treatment changes. Blueprint and hologram decorations stay
inside that frame. The installed popup remains 360x56 including its peak meter.

## Actual depth, native playback

`web/scene.js` builds tube, sphere, cylinder and instanced-particle geometry.
The scenes use depth testing, shadow maps, directional and rim lighting,
perspective (orthographic for the isometric style), shaded surfaces and restrained
surface glow. The 3D models are rendered into 96-frame, double-resolution PNG
atlases per design. `src/atlas.rs` blends adjacent rotation frames in Cairo.
This is playback of rendered 3D scenes, not a live WebGL renderer in the popup.
Speech still controls phase, speed, compression and phrase transitions in real time.

The native player uniformly scales each frame, preserving proportions, and clips
effects to a common two-pixel margin. It caches only two atlases for transitions.
No browser, GPU rendering service, internet connection or Node process is needed
for normal dictation. `draw_legacy_style` retains the prior procedural renderer
for visual comparison only; it is not the active rendering path.

## Preview and reproduce

1. Run `cargo run --locked --example molecule_export -- web/molecule.json`.
2. In `web`, run `npm ci --ignore-scripts`, then `npm start`.
3. Open `http://127.0.0.1:5247/` to compare designs at enlarged and actual size.
4. Open `http://127.0.0.1:5247/?bake=1` to export all ten atlases to `assets/`.
   Use `&only=4,9` for selected style indexes. The server accepts exports only
   from its exact loopback origin and validates the PNG signature and size.
5. Optimize the exports with ImageMagick: `magick mogrify +dither -colors 256
   -define png:color-type=3 -define png:compression-level=9 -strip assets/*.png`.
6. Run the native tests and rebuild before installing the executable.

The Three.js version is pinned in `web/package-lock.json`. No reference-site
source code or imagery is embedded. The Web Design plugin's Granular Orbit and
Holographic Roster directions informed the persistent particles and layered
depth. References: https://lusion.co/about/,
https://threejs.org/docs/pages/MeshPhysicalMaterial.html and
https://www.rcsb.org/structure/1BNA.

## Speech response

Relative audio-envelope onsets, processed at the full 100 Hz audio rate rather
than the display refresh rate, estimate speech cadence. Faster pulse cadence
smoothly increases rotation and tightens the artistic helices; pauses release
the compression. This is an acoustic approximation, not measured words per
minute or speech recognition. Loudness alone does not imply fast dictation.
The strand keeps visibly rotating even during quiet input. Pause detection
uses a relative speech threshold so room noise need not fall to digital silence.

After at least 0.7 seconds of voiced activity, a 650 ms pause can start a
1.2-second crossfade. At least two seconds separate transition starts. A short
breath does not advance the sequence. A 12-second maximum dwell starts a fade
during continuous speech so the rotation cannot become stuck waiting for a pause.
Ending a phrase and starting another
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

The measured fragment is repeated horizontally to fill the shared strand frame,
not stretched along its axis. Each copy retains its internal measured geometry;
the repeated assembly and connections between fragments are not a measured
long molecule, and no chemical bonds are invented between copies. Its rendered
rotation is played from the same kind of atlas as the other designs.

## Verification

Run `cargo test --locked --bin voxtype` for cadence, pause transitions, geometry,
rendering and voice-response tests, including pixel bounds for all ten designs
at three popup sizes, four rotations, and three response levels.
Tests also check the detailed style catalog, full-turn continuity and bounded cache.
`cargo run --locked --example helix_render
-- /tmp/helix-renders` exports every style at 360x56 and 480x100.

`web/verify.mjs` uses Playwright to check all ten styles at 1280x800 and 390x844,
including real canvas pixels, light/shadow range, names/descriptions, controls,
page overflow, moving frames and reduced motion. It saves screenshots and a JSON
report. Set `PLAYWRIGHT_MODULE` to an installed Playwright module, or install it
in the authoring environment. `PREVIEW_URL`, `CHROMIUM_PATH` and `EVIDENCE_DIR`
are optional overrides. These automated browser checks do not substitute for
checking the native popup on the actual compositor.

The inherited library-wide tests currently need separate repairs: the manifest
omits the `tempfile` test dependency, and old theme tests call `set_var` without
Rust 2024's required unsafe handling. These unrelated tests are not modified.
