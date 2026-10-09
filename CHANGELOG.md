# Changelog

## 2026-09-22 — Initial portable desktop collection

- Recovered current desktop settings, custom shell plugins, voice controls, launchers, screensaver, templates, and source modifications from local files and available task history.
- Prepared a GitHub project with install preview, timestamped backups, restore protection, explicit capture allowlist, regression tests and CI.
- Replaced fixed home paths with install-time rendering and generated monitor/workspace mappings for each PC.
- Preserved original hardware and AI service configurations locally; public examples use placeholders.
- Added source builds for the custom photo viewer and colored voice popup, with stock fallbacks.
- Documented new-PC setup, account sign-ins, hardware-specific tasks, provenance and known verification limits.

## 2026-09-30 — Public Omarchy consolidation

- Named the public repository omarchy and indexed 78 Codex/Claude source conversations, avoiding imported-Claude duplicate records.
- Used the local JEV harness to recommend models for each scoped source conversation; no task settings were changed.
- Refreshed desktop code for the latest dictation fixes, prompt expansion, rainbow borders, mouse settings, workspace number bindings, Herdr menu repair and TaskGrid.
- Added portable workspace-picker/RDP mappings and optional Edge menu source.
- Removed machine identifiers, personal account/vocabulary fields, private feeds, original hardware snapshots and unverified portrait artwork from the public tree.
- Protected adapted files from capture and documented current behavior and new-PC verification limits.

## 2026-10-02 — Windows VM, scans and storage

- Consolidated the Windows/scanning/storage topic under Omarchy with a dedicated setup and recovery guide.
- Captured the working VM reconnect launcher and adapted the RDP software-rendering/fixed-size workaround to generated monitor mappings. Credentials remain local and reach the client through stdin.
- Generated zero-gap workspace 2 rules alongside the existing maximize/monitor rule.
- Documented 4-vCPU, 8-GiB RAM, 512-GiB virtual capacity preferences and the still-unallocated guest disk space; no partition change is performed by setup.

## 2026-10-09 — Sidebar Apps menu and keyboard navigation

- Hide Sunshine from the tray and add a text-only `apps` button.
- Open the installed application menu beside the sidebar on its monitor, capped at 580 pixels with scrolling and the existing application search/launch behavior.
- Space alone focuses the sidebar at Gmail; Up/Down select launchers, Enter activates, and Escape releases focus. The binding intercepts normal typing spaces; change it to `SUPER + SPACE` to preserve typing.
- Runtime IPC confirmed 72 app rows, 300-by-580 panels on both monitors, Gmail selection, and a registered unmodified Space binding with no Hyprland config errors. Native desktop clicking, scrolling and key delivery were unavailable and remain unverified.

### Animated translucent Apps panel

- Add an animated translucent tie-dye background and 320ms downward reveal.
- Extend the popup to the bottom edge of its monitor and clip the app list to the actual card height, fixing rows painting outside the former 580px box.
- Restore the first app after opening and hide duplicate ChatGPT tray entries while retaining the Codex launcher.
- Runtime IPC confirms app population and animation; native click, scroll and visual triple-check verification remain unavailable in this chat environment.
