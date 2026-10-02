# Windows VM, scans and storage

This is the portable configuration and operational guide for the Windows VM,
shared scans, external storage and backup topics consolidated under Omarchy.
It is not a Windows image or a backup of private documents.

## Desired behavior and verified source-machine state

Keep the existing Windows installation, applications and files. Open the RDP
window on workspace 2, maximized beside the sidebar. The installer assigns
workspace 2 to the first monitor in its generated workspace map; choose that
monitor explicitly with `--monitors` on a new computer.

The October 2 source-machine repair was verified with a visible Windows desktop,
workspace placement and a reconnect that reused one RDP window. Its VM resources
were verified in the container/QEMU configuration: 4 vCPUs, 8 GiB RAM, and a
512 GiB virtual disk. These preferences are not automatically applied to a VM by
this repository. CPU cores remain shared with the host.

The virtual image was expanded, but the guest C: partition remained approximately
127 GiB, followed by a recovery partition, with roughly 384 GiB unused. Increasing
virtual capacity alone does not enlarge C:. No guest partition repair or full
current-image backup was completed as part of this repair. A second data volume
or an expanded C: remains a separate decision. The disk is sparse: 512 GiB is its
capacity, not fully reserved physical storage. Monitor the hosting filesystem's
free space as Windows writes more data.

## Launch and display

`~/.config/omarchy/bar/launch-windows` focuses an existing window, reconnects to
an already listening local guest when local credentials are available, or invokes
Omarchy's supported VM start/install flow. Reconnect avoids another Docker
administrator prompt when Windows is already running. A listening port alone
does not prove that Windows login will succeed.

The private optional credentials file is `~/.config/windows/credentials`, with
`USERNAME` and `PASSWORD` lines in KEY=VALUE form. Keep it readable only by its
owner. It is not distributed or captured here. The wrapper also accepts the RDP
arguments supplied by Omarchy. An optional local `krb5.conf` is used only if present.

The wrapper calculates the generated primary monitor's available area, subtracts
reserved panels, removes the floating toolbar, and uses software rendering with
fixed resolution. This combination resolved the source machine's X11 window
errors and cropped display. Software rendering may cost more CPU and be less
smooth for video than accelerated graphics. Monitor changes require reconnecting;
this is intentionally not dynamic resizing. On another PC, verify a real Windows
desktop, its taskbar, sidebar clearance and reconnect behavior after installation.
Clipboard, sound and microphone redirection remain enabled in the default local
connection. The existing localhost certificate-ignore behavior is retained; it is
not a configuration recommendation for an untrusted remote RDP server.

## Scanning and shared files

The universal Linux scan folder is `~/Windows/Scans`. Inside the Docker Windows
VM, use `\\host.lan\Data\Scans`, or the corresponding mapped share when configured.
The generated VM config must bind `~/Windows` to the guest's shared data folder.
A claim-specific subfolder is not the universal scan root. The host shared folder
is separate from Windows C: and from any proposed second Windows volume.

Create the directory locally if missing, confirm the bind mount and permissions,
and select the share in the scanner software. Canon R30 work used CaptureOnTouch
Lite inside Windows; discover USB identifiers on the destination PC instead of
copying source-machine bus numbers. Verify one non-sensitive scan opens from both
Linux and Windows. Configure printers separately and print a test page. No scan
contents, client folder listings, device serials or account logins belong here.

## Storage and recovery

Before moving the VM, shut Windows down gracefully, verify QEMU has exited, and
make a verified copy of the complete VM storage directory and private runtime
configuration. Copying a running sparse image is not a consistent backup. Preserve
sparsity and check destination free space. Keep the original until a boot and file
check succeed from the copied image. Never run two VMs against the same writable
disk image. To use the same running Windows from another PC, connect remotely to
one host; configure trusted network access separately.

The source machine uses an external-drive-backed `~/.windows` path. Mount paths
and filesystem identities must remain machine-specific. Verify that the intended
filesystem is mounted before launch; a missing mount must not cause a fresh VM
to be created on the root disk. Friendly device names and file-manager shortcuts
are presentation only; they do not change storage capacity or move files.

For C: expansion, the intervening recovery partition must be handled deliberately.
First verify a current backup; preserve/recreate recovery functionality and then
verify both Windows capacity and recovery status. Adding a second data volume
avoids moving the existing recovery partition but leaves C: at its current size.
Neither choice creates an independent backup. This repo performs neither action.

If startup fails, inspect mount availability and the actual VM/container status.
Omarchy's privacy preflight can reject inherited setgid flags on the VM/share
directories; the launcher clears that flag on those existing directories only.
Do not recursively loosen file permissions. Roll back launcher settings using the
installer's receipt-backed restore process in [new-pc.md](new-pc.md); it does not
roll back a Windows disk, partition edits or VM resources.

## Related storage project scope

The consolidated project also includes NAS software/backups, Raspberry Pi backup
media, drive naming and NVMe removal guidance. The historical NAS task established
a destination but had not verified personal-file copying. The Raspberry Pi task
reported a mount-lifecycle issue requiring further repair. These are historical
limits, not verified current service status. Source references are in THREADS.md.
No NAS backup, Pi deployment or hardware operation is installed automatically.
Use `profiles/examples/` for generic device-naming examples; keep actual hardware
profiles and credentials outside version control.
