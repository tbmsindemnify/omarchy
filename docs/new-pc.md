# Install on another PC

## Base system

Install and boot Omarchy first. This repo targets its Lua Hyprland/Quickshell architecture; it does not work on older hyprland.conf/Waybar releases without adaptation. Reference versions are in `versions.txt`. Run setup as your regular desktop user, never root.

```bash
git clone https://github.com/tbmsindemnify/omarchy.git
cd omarchy
./install.sh       # Preview only
./setup.sh        # Dependencies, source builds, settings, theme, activation
```

Full setup downloads Arch/Rust dependencies and the `base.en` model, builds the customized photo viewer and colored popup, backs up/replaces managed settings, selects Kanagawa, configures image defaults and activates the desktop. Administrator authentication for packages occurs in your terminal. On failure it stops; fix the reported prerequisite and rerun. `./install.sh --apply` applies settings only, with standard-popup/stock-viewer fallbacks.

## Monitors and input

By default the focused display owns workspaces 1–5, the next 6–10, etc. Choose an explicit order with `./setup.sh --monitors eDP-1,DP-1`. Generated workspace mappings are shared by Hyprland, the sidebar, the workspace picker, and RDP sizing. New monitors use native resolution/automatic positioning. Edit `~/.config/hypr/monitors.lua` for physical layout; reapplying setup replaces it with a backup.

The current pointer preference is flat acceleration with sensitivity 0.55. Tune it for your mouse. The border preference is a rotating five-pixel rainbow with inactive dimming. See [voice-commands.md](voice-commands.md) for current buttons; the earlier two-button chord has been superseded.

## Voice and models

Setup downloads the smaller base.en speech model for portability. The original desktop uses large-v3-turbo and flash attention. Select/download a larger model with Voxtype only when the destination supports it. Test dictation into a disposable document before relying on it. The optional conversational command/rewrite helpers depend on a local Ollama model; no large model download is triggered automatically.

For a separately built colored popup, run `./scripts/build-osd.sh`, `./install.sh --apply --with-osd`, and `./scripts/activate.sh`. To switch back, first disable its service with `systemctl --user disable --now voxtype-color-osd.service`, then install without `--with-osd`. The colored sidecar derives from Voxtype 1.0.1; check its behavior when upgrading the daemon.

## TaskGrid

The widget source and launcher are installed and autostarted. Super+Shift+T toggles it. The public config retains the visual style but omits fixed monitor coordinates, existing tasks and feed contents. `show_sessions` is false and `local_feeds` is empty initially. Enable sources deliberately in `~/.config/taskgrid/config.json`. Feed scanners read locally; they do not upload data. Adapt the generic project/vault paths in `feeds.py` if using those optional sources.

## App launchers

Install the external applications you use, then sign in normally. Codex/ChatGPT requires `chatgpt`; Claude requires `claude-desktop`; Herdr uses Omarchy's terminal launcher; Edge can invoke the Omarchy browser-install flow. No proprietary application binary is bundled.

Keeper preserves the original Edge Profile 2 preference. Create/select that profile or edit the launcher. Its autostart line can be removed if not wanted. Gmail uses the first signed-in account, not a hardcoded owner email.

Hermes requires its CLI. The helper uses the local desktop build if present and otherwise its loopback dashboard. Install/configure Hermes separately; no credentials or full JEV/Hermes application is bundled. The source-task index records that separate work.

## Optional Edge workspace menu

After installing managed files, run `python3 scripts/install-edge-menu.py`. Open `edge://extensions`, enable developer mode, and load `extensions/edge-workspace-menu` as an unpacked extension. The manifest's public key stabilizes its ID; no private key is included. The native host validates the origin, workspace number, focused Edge window and tab title before moving the window. Alt+right-click works without this extension.

## Windows, scanning and printers

See [Windows VM, scans and storage](windows-scans-storage.md) for the launcher, resource settings, disk-capacity caveat and recovery steps.

Provision Windows using Omarchy's supported VM installer or migrate the VM separately. No VM disk, license, credentials, browser login or Windows apps are included. The RDP wrapper sizes the desktop beside the sidebar on workspace 2.

The established shared folder convention is `~/Windows/Scans` on Linux and `\\host.lan\Data\Scans` inside the Docker Windows VM. Create the folder and verify the bind mount in that PC's generated VM config. Scanner USB IDs and bus paths differ by machine. Canon R30 work used CaptureOnTouch Lite in Windows; test one scan on the new machine. Configure the HP printer through the new PC's print settings and verify a test page.

## Storage, Bluetooth, remote access and local AI

Generic examples live in `profiles/examples/`. Original drive UUIDs, Bluetooth addresses, mount paths, client bookmarks and VPN/SSH identities are not public defaults. Adapt naming/reconnect examples deliberately; no partition, encryption or `/etc` mutation is part of the installer.

Local Ollama/Open WebUI, Hermes/JEV routing, experimental computer-use agents, phone access and Tailscale are separate integrations recorded in THREADS.md. Install and size models to the new hardware, enroll remote devices afresh, and authenticate each provider. Do not copy runtime secrets or expose unauthenticated loopback services to a network.

## Recovery and future updates

Installer backups are printed under `~/.local/state/tbm-omarchy/backups/`. Restore with `python3 scripts/manage.py restore EXACT-BACKUP-DIRECTORY`, then reload the desktop. Restore refuses to destroy subsequent edits without `--force`.

File rollback does not uninstall packages/models, remove compiled binaries, revert MIME preferences or disable services. Those are separate optional steps:

- Stop the colored popup with `systemctl --user disable --now voxtype-color-osd.service`.
- Restore photo defaults with `xdg-mime default imv-dir.desktop image/jpeg image/png image/webp image/heif image/avif image/tiff image/gif image/bmp`.
- Choose your previous theme in Omarchy's theme menu.
- Stop TaskGrid with `taskgrid stop` before removing its autostart/launcher.

Pull repository updates, preview the installer, then apply. Capture only allowlisted unprotected files; `capture: false` files intentionally differ from the source machine. Public preflight must pass before committing or pushing any new customization.
