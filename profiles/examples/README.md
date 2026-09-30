# Machine-specific examples

These are templates, not the original PC identifiers. The installer does not apply them.

- For monitors, use `./install.sh --monitors eDP-1,DP-1` and edit your local monitors.lua for physical layout.
- For friendly disk names, replace REPLACE_WITH_FILESYSTEM_UUID in the udev example with the intended drive UUID from `lsblk -f`. Device display names do not change partitions or labels.
- For Sonos, pair the speaker, then substitute its address in the reconnect script before adding a timer.
- Keep personal profiles under ignored `local/`. Do not commit device credentials, VPN identities, account URLs, client bookmarks or VM images.

Original machine-specific snapshots remain local outside this repository; public defaults are generated.
