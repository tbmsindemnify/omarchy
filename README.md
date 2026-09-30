# Tyler's Omarchy

My personal desktop setup, rebuilt from the Omarchy customizations made in September 2026. Install Omarchy on another PC, clone this repository, and apply the same desktop preferences.

Includes the wider themed sidebar, larger workspace buttons, outline app launchers, independent five-workspace monitor groups, voice dictation and desktop commands, selected-text prompt expansion, rainbow focus borders, TaskGrid, mouse-button Enter, multicolor Matrix screensaver, terminal preferences, photo-folder navigation, and document templates. Optional integrations cover Windows/scanning, Hermes, local AI, printers, Bluetooth, and storage presentation.

## Consolidated history

[THREADS.md](THREADS.md) gathers **78 source conversations: 33 Codex and 45 Claude**, with scoped summaries, source identifiers, and JEV-generated model suggestions. It also records five earlier recovered ChatGPT background topics.

## Set up another PC

Install Omarchy first using its official installation instructions. This repo is a personalization layer, not an OS image. The tested baseline is Omarchy **4.0.4**, Hyprland **0.56.2** (Lua config), Quickshell **0.3.1**, and Voxtype **1.1.0** (custom popup derived from 1.0.1). Check compatibility before applying to another release.

```bash
git clone https://github.com/tbmsindemnify/omarchy.git
cd omarchy
./install.sh                         # Preview files before changing anything
./setup.sh                           # Dependencies, local builds, settings, theme and activation
```

Run setup as your normal user in a terminal on the new desktop. Package installation requests administrator authentication. It downloads the speech model and build dependencies; account sign-ins and hardware connections are completed separately. **Do not run setup as root.**

The focused monitor gets workspaces 1–5, the next gets 6–10, and so on. To choose explicitly, run `hyprctl monitors` and pass connectors in your preferred order:

```bash
./setup.sh --monitors HDMI-A-1,DP-1
```

For settings only, without installing packages or restarting anything:

```bash
./install.sh --apply
```

This uses the standard dictation popup until the optional colored popup is built. The photo launcher uses stock imv until its custom build exists. See [new PC setup](docs/new-pc.md) for the complete steps and [the recovered change inventory](docs/change-inventory.md) for coverage and limitations.

## Keep evolving

Ask the agent to “update my Omarchy setup and the omarchy repository.” This repository includes maintenance instructions in AGENTS.md.

For edits made directly in your desktop settings:

```bash
python3 scripts/manage.py capture             # Preview changes to known managed files
python3 scripts/manage.py capture --apply     # Copy those changes into the repo
python3 scripts/check.py
python3 -m unittest discover -s tests -v
git diff                                     # Review before committing
git add home manifest.json docs CHANGELOG.md
git commit -m "Describe the desktop change"
git push
```

Capture only reads the explicit manifest. New files must be added deliberately. The main Hyprland entrypoint, monitor layout, and workspace widget are excluded from capture because their portable versions differ from the original desktop; edit these in the repo and update the installer when needed. Files marked `capture: false` are protected portable templates. Hardware configurations in `profiles/` are generic examples and are not automatically captured or applied. No background process uploads your home directory.

On another PC, pull new commits, preview `./install.sh`, and apply. Preserve any intentional machine-specific overrides before applying; installed managed files are replaced, with backups. Choosing `--with-osd` again is necessary if you want to retain the custom popup setting.

## Undo a settings installation

Every changed file has a backup and receipt under `~/.local/state/tbm-omarchy/backups/`. The installer prints the exact path.

```bash
python3 scripts/manage.py restore ~/.local/state/tbm-omarchy/backups/EXACT-BACKUP-DIRECTORY
```

Restore refuses to overwrite subsequent edits unless `--force` is supplied. Reload the desktop afterward. This restores managed files only; package installation, theme changes, MIME defaults, model downloads, built binaries, and service enablement are separate steps described in the setup guide.

## Layout

- `home/`: portable, allowlisted user files; `@@HOME@@` is filled during installation.
- `scripts/`: installation, capture, checks, activation, and optional source builds.
- `vendor/`: custom imv and Voxtype popup sources, including upstream licenses.
- `profiles/examples/`: generic machine-specific templates, without owner device identities.
- `docs/`: setup guide, voice commands, provenance, versions, and package inventory.
- `tests/` and `.github/workflows/`: installer regression tests and CI.

Credentials, business files, browser sessions, original chat transcripts, model weights, Windows images, and private keys are excluded. Upstream component licenses remain in their source directories; see [third-party notices](docs/third-party.md).
