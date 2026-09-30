# Current voice and mouse controls

This describes the September 30 source. It supersedes the original September 21 two-button gesture and automatic command-mode experiment.

- **Button 5:** click to start dictation, speak, click to finish. Always dictates.
- **Super + button 5:** start an explicit voice command; button 5 finishes it.
- **Button 4 without selected text:** Enter.
- **Button 4 with selected text:** expand the selection into a structured task prompt. The expansion is not automatically submitted.
- **Onboard thumb paddle mapped to XKB code 191:** Enter on release. This depends on mouse firmware mapping; it is not universal to all mice.
- **Alt + right-click:** move the pointed-at window to one of the current monitor's five workspaces.
- **Super + Shift + T:** collapse/expand TaskGrid.

## Dictation delivery

Recordings can run for ten minutes; transcription waits up to three minutes. Button debounce prevents an accidental immediate stop. Speech is saved in a private runtime recovery file and copied to the clipboard. The controller chooses the window active when recording stops, returns focus to it after transcription, and sends the appropriate paste chord. Terminal classes/tags use Ctrl+Shift+V; other applications use Ctrl+V. If the target has closed, the current implementation falls back to the active window.

That focus recovery is a deliberate change from the earlier cancel-on-any-focus-change dictation behavior. Explicit voice commands still validate their original target. Text-box accessibility is used by other helpers but no longer makes ordinary button 5 enter command mode.

The portable setup starts with the smaller `base.en` speech model. The original machine later used `large-v3-turbo`, flash attention, and a specialized vocabulary. Install/select larger models only when the new machine supports them. No audio or model weights are in this repo.

## Command vocabulary

The action catalog is read from live Hyprland bindings. Examples include “make this window fullscreen,” “move window left,” “switch to workspace three,” “take a screenshot,” “print this document,” and “create file named meeting notes dot txt.” Printing opens the current app's print UI. File creation does not overwrite existing files.

The newer conversational command interpreter and rewrite helpers can use a local Ollama model at 127.0.0.1:11434. Deterministic aliases work without a model; free-form requests depend on the local service/model. The project does not silently download multi-gigabyte AI models or publish any chat contents.

`tests/voice-catalog.json` is a saved command-name fixture for unit tests, not a promise that every new PC exposes exactly the same actions. Test basic dictation into a disposable document and a harmless command after installation.
