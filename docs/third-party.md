# Third-party code and assets

This is a public collection of personal configurations and modified upstream components. It does not change the licenses or ownership of bundled upstream code, app trademarks, or artwork.

- `vendor/imv`: imv 5.0.1, upstream https://git.sr.ht/~exec64/imv at `bdec0e527be289e08c3a70c8719a85994d26bd4d`, plus local `src/imv.c` changes, `src/photo_scroll.h`, and geometry test. Upstream MIT license is in `vendor/imv/LICENSE`.
- `vendor/voxtype-color-osd`: the minimal GTK4 sidecar assembled from Voxtype 1.0.1 source with local colors/renderer changes. Original source was downloaded to the prior sidebar task's `work/voxtype-theme/voxtype-1.0.1`. Includes the upstream `LICENSE`; the committed Cargo.lock fixes dependency versions. This is an OSD sidecar, not a replacement speech engine.
- `home/.config/omarchy/plugins`: local clones of Omarchy's bar, workspace and idle components, customized in the user's config directory. Baseline installed package: Omarchy 4.0.4. Upstream: https://github.com/basecamp/omarchy . The upstream license text is saved as `OMARCHY-LICENSE`.
- Simple outline sidebar logos came from the existing custom launcher bundle. App names and marks remain their owners' property. Portrait PNG artwork was omitted from this public collection.
- This repo does not vendor the Omarchy OS, proprietary desktop apps, Windows, or speech/LLM weights.
