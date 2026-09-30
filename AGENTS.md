# Maintaining this personal Omarchy setup

This repository is the portable source of truth for Tyler's desktop preferences.

- Keep desktop customization in user-owned paths. Never patch /usr/share/omarchy.
- Read README.md, docs/new-pc.md, and manifest.json before changing installation.
- Never commit credentials, cookies, account tokens, private keys, client files, Windows disks, model weights, or chat transcripts.
- Add new managed files explicitly to manifest.json; capture must remain allowlisted.
- Use @@HOME@@ in templates, and generate monitor/workspace mappings during installation.
- Machine-specific UUIDs, Bluetooth addresses, mount paths and GPU assumptions belong in profiles or ignored local/, never portable defaults.
- Keep previews free of writes; back up existing files before install; do not reload the user's active desktop merely to test the installer.
- Ordinary button 5 must always dictate; commands require Super+button 5. Preserve the current dictation refocus/paste recovery and explicit command target checks.
- Run python3 scripts/check.py and python3 -m unittest discover -s tests -v.
- Record changes in CHANGELOG.md and update recovery/setup instructions when behavior changes.
- Future personalization requests include updating this repository when available. Review the diff and secret scan before committing/pushing changes authorized by the user.

- This repository is public. Keep private runtime configuration outside it; profiles/examples contains placeholders only. Respect manifest capture:false entries and never copy raw transcripts or private TaskGrid feeds.
