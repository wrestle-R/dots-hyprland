# Image states

Five native SVG icons matching the dark desktop: failure (broken document), no
image (empty picture frame), unknown app (neutral window), loading (rotating
ring), offline (crossed Wi-Fi). Assets belong to Quickshell, leaving the global
Breeze theme untouched.

Install after the existing clipboard/sidebar/settings customizations:

```bash
python3 End-4/image-states/customizations.py check
python3 End-4/image-states/customizations.py install
```

In the dots repo use `dots/.config/hypr/custom/image-states/customizations.py`.
The same package is included in both repositories. The installer preserves
upstream source QML in the dotfiles checkout; it applies checked changes to the
live config. It stops on unknown upstream/personal edits before writing and
backs up only changed files under `~/.local/state/hypr-image-state-backups`.
Use `restore --backup <printed-backup-directory>` to undo an installation;
restore refuses to overwrite later edits. Reapply after upstream setup updates.

App fallbacks cover dock, workspace icons, window overview, region selection,
notification app icons and volume mixer. AppSearch resolves unknown windows to
the neutral app asset. File previews use no-image for unknown MIME icons and
failure for unreadable images. Clipboard previews show decoding/loading and
failure separately. Notification pictures and foreground media artwork opt into
content placeholders; decorative backgrounds remain unchanged.

`StyledImage.showPlaceholder` opts a content image into automatic state handling.
`placeholderState` can supply a known state from an external decoder. Blank
source means no-image, Qt Loading means loading, and Qt Error means failure.
A failed HTTP(S) source becomes offline only when the existing Network service
reports neither Ethernet nor connected Wi-Fi. This is link status, not an
internet reachability check; cached/local media failures stay failure. There are
no extra network probes and no claim that every failed request means offline.
Loading animation runs only while the placeholder is loading and visible.

Verification: isolated native Quickshell preview and actual empty/error/ready/
offline source transitions; SVG rendering at desktop scale; installer install,
idempotency, unknown-edit refusal and rollback; live shell reload and existing
integration checks. No environment files or secrets are involved.
