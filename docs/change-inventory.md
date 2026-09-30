# Current implementation inventory — 2026-09-30

The source history is consolidated in [THREADS.md](../THREADS.md) and the machine-readable [thread index](thread-index.json). Live user files were reconciled against Codex and Claude records. Later settings take precedence over older plans.

| Area | Included | Limits |
| --- | --- | --- |
| Shell/sidebar | Custom bar, idle/workspace plugins, larger buttons, mail and app launchers | Requires Omarchy 4.0.4-era Quickshell API |
| Appearance | Kanagawa preference, terminal font settings, spinning rainbow active border and inactive dimming | Theme/monitor behavior requires a real desktop check on the destination |
| Mouse/keybindings | Button 5 dictation, explicit Super+button 5 commands, button 4 selected-text prompt/Enter, paddle mapping, numeric workspace key fix | Paddle mapping depends on device firmware; pointer sensitivity is personal |
| Voice | Latest controller, clipboard/paste/focus recovery, 600s recordings, helpers and tests | Portable default uses base.en; source PC uses a larger model; microphone round-trip is not reproduced by unit tests |
| Workspace picker | Alt-right-click helper, portable mapping, optional Edge native-messaging extension | Extension must be loaded in Edge; no private signing key included |
| TaskGrid | Current GTK4 widget source, launcher, appearance defaults and toggle | Session discovery and private feed scanning start disabled; no actual tasks/feed contents included |
| Windows | Reuse existing RDP window, size desktop to available monitor, preserve sidebar, VM-specific zero-gap rule | No VM image, credentials, Windows applications, or universal USB configuration |
| Photos | Custom imv source and geometry test; folder launcher with stock fallback | Known upstream keyboard repeat race is not claimed fixed |
| Dictation popup | Minimal colored GTK4 sidecar source and build script | Derived from Voxtype 1.0.1; current daemon is 1.1.0; verify compatibility after upgrades |
| Templates/screenshots | Blank Writer/text templates, larger annotation preference, branded Matrix screensaver | XDG directory customization may require adjustment |
| App integration | Claude/Codex focus-or-launch, Herdr menu fix, Keeper, Hermes, Edge/mail shortcuts | Install and authenticate external apps separately |
| Storage/audio/scanners/AI | Generic profile examples and documented setup history | Hardware/account-dependent configurations and separate AI applications are not auto-installed |

## What changed for public portability

Home directories are rendered at install time. Monitor workspace groups are generated as Lua, JavaScript and JSON from the same list. RDP sizing and the workspace menu use that map. Device serials/UUIDs, private bookmarks, VPN identities, account-specific Gmail URL, personal dictation vocabulary, chat transcripts, task feeds, model weights and VM images are not published. Portrait artwork with unverified redistribution provenance was removed; simple outline icons remain.

Files with `capture: false` in the manifest have deliberate portable transformations. Edit those in the repository; do not overwrite them with private machine versions. New source files require explicit manifest entries.

## Validation and limits

The installer tests cover preview, repeat installation, backup/restore, later-edit protection, symlink refusal, invalid monitor input, missing custom popup, and allowlisted capture. Voice unit tests use a saved command-name fixture and mocked desktop operations; they do not operate a live window. Photo geometry and source builds were validated during the initial collection. Syntax/secret-pattern checks are repeated before publication and CI checks the portable installer/photo geometry.

This is a personalization layer on an existing compatible Omarchy installation, not a new OS ISO. It has not been installed on a second physical PC. Whole-desktop rendering, real microphone delivery, TaskGrid positioning, scanner passthrough and printing on another PC remain unverified. The source PC's active desktop was not reapplied while creating the repository.
