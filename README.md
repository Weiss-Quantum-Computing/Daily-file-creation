# Daily2.py

Automates the daily folder/file setup that the Weiss lab used to do by hand every day: creating that day's data folders and seeding a starter log file.

## What it does

Each time it's run, `Daily2.py` targets the current date (`YYYYMMDD`, from the system clock) and:

1. **Camera folder** — creates `<DDScontrol>/../CameraControl/<date>/` if it doesn't already exist, and pre-populates `log.txt` inside it whenever that folder has no `log.txt` yet — also when the folder already existed, e.g. because CameraGui made it first (see [Log auto-population](#log-auto-population) below). An existing `log.txt` is never touched.
2. **DDS folder** — creates `<DDScontrol>/<date>/` if it doesn't already exist, then, only with `SeedDDSScripts = 1` (default `0` since 2026-11-02: the DDS control GUI replaces the scripts, see dds-control's README), seeds it with the DDS scripts listed in `DDSFileNames`: each script missing from today's folder is copied from the most recent dated DDS folder that has *that* script (searching back up to 90 days, per file). This also happens when today's folder already exists — the DDS GUI creates it itself, with only its own files, when it starts first — and a script already in today's folder is never overwritten. A script found in no folder of the last 90 days is skipped with a note, not a crash. (Before 2026-10-23 the search stopped at the first dated folder, so one GUI-made folder dropped every script from all later days.)
3. **PSUBox folder** — creates a matching dated folder in the Box Sync tree (`DirectoryPSUBox`).
4. **Log copy (optional)** — if `CopyLog = 1`, copies that day's `log.txt` into the PSUBox folder as `log2.txt`, timestamping and keeping any previous `log2.txt` as a backup instead of overwriting it.
5. **DDS GUI state snapshot** (`SnapshotGUIState = 1`, added 2026-09-04) — the DDS GUI ([Freq-Scan-GUI](https://github.com/Weiss-Quantum-Computing/Freq-Scan-GUI), installed at `<DDScontrol>/WeissDDS/Freq-Scan-GUI`) works in the same `<DDScontrol>/<date>/` folder: its pulse files and compiled run files overwrite themselves there, and its `dds_log.txt` records every compile, run and calibration change with the time. Once per day this step copies the GUI's calibration state (`f4new.npy`, `freq_offset.npy`, `transition_cal.json`, `panel_config.ini`, `session_state.json`, `type_memory.json`) into `<DDScontrol>/<date>/gui-state-at-start/` together with `gui-version.txt` (the GUI's git commit, read from `.git` without needing git installed), so the day's changes in `dds_log.txt` can be read against the day's starting point. Skipped with a note if the GUI is not installed; the GUI creates the dated folder itself if it starts before this script has run, and the snapshot still happens on the next run of the script.

Each of these behaviors is gated by its own flag (`CreateCameraFolder`, `CreateDDSFolder`, `SeedDDSScripts`, `CreatePSUBoxFolder`, `CopyLog`, `SnapshotGUIState`) — set any of them to `0` to skip that step (`SeedDDSScripts` is `0` by default). If a target folder already exists, the script prints that it already exists and never overwrites or removes anything in it; the only things it adds to an existing folder are a missing `log.txt` (step 1) and missing DDS scripts (step 2) — **re-running the script on a day that's already been set up is always safe.**

## Log auto-population

New `log.txt` files are no longer created blank. Instead the script looks at the most recent previous day's log (searching back up to 90 days) and carries forward:

- The `MOT`, `OP`, and `EO zeros` lines. Each of these has the form `label (old values) --> (final values)`; the script takes the **final** (second) parenthesized group from the previous log and uses it as *both* groups in the new log, so the previous day's ending values become the new day's starting point (and are still there to edit if anything changes).
- **Any freeform notes** typed between the `EO zeros` line and the column header in the previous log. These are copied forward verbatim, grouped under the MOT/OP/EO zeros lines. This is meant for running notes (e.g. "recalibrate laser X", "fridge base temp holding at 3.1K") that should persist day to day — just delete a note from a given day's log once it's no longer relevant, and it won't carry forward again.
- The reusable column header (`#  LV  LH  RV  RH  Result`).

See [`example-logs/20260630-log.txt`](example-logs/20260630-log.txt) for a real log in this format.

If no previous log is found within 90 days, the new log just gets the date and header, and a note is printed.

## What's in this repo

```
CameraControl/
  Daily2.py          the script itself
DDScontrol/
  Freqscan.py, Freqscan2.py, Freqscan-RF.py, Cool_Cal.py, Coolscan.py,
  Rabi.py, Rabi-RF.py, DDScool.py, DDSaddress.py, DDSpostcool.py,
  Phasescan.py, Phasescan-RF.py, DDSarb.py, Powerscan.py, Powerscan-RF.py
example-logs/
  20260630-log.txt   reference log showing the expected format
```

`CameraControl/` and `DDScontrol/` are laid out as siblings on purpose, matching the folder structure `Daily2.py` expects relative to its own location (see below). The DDS scripts under `DDScontrol/` are exactly the files `DDSFileNames` seeds into each new dated DDS folder — they're included here so the tree this repo checks out is actually runnable, not just the script in isolation.

**These DDS scripts are snapshots, not the source of truth.** The most up-to-date versions of the files in `DDScontrol/` should always be found on the camera control computer itself, or in the separate DDS-control repository — check there before relying on the copies here for anything beyond seeding a fresh folder layout. They were last re-synced on 2026-10-24, byte for byte, from `dds-control/scripts/` at commit fe0f388 (its `fixes-2026-10-15` review-fix branch, which adds the compile-failure checks and refuses to run in `DDScontrol` itself); `Rabi.py` and `Rabi-RF.py` are retired there and stop with a message when run (use Freq-Scan-GUI's Power Scan with quadratic steps instead). Re-sync them from dds-control rather than editing them here.

## Things to know before running this

- **Windows-only as written.** It calls `os.startfile(...)` to open each newly created folder in Explorer, and `PathToSciTE` points at a Windows `.lnk`. It will not run as-is on macOS/Linux.
- **`DirectoryCamera` and `DirectoryDDS` are derived automatically** from this file's own location — the script assumes it lives inside the `CameraControl` folder, with `DDScontrol` as a sibling folder next to it (`.../CameraControl/Daily2.py` and `.../DDScontrol/`). Nothing needs editing here as long as that layout holds.
- **`DirectoryPSUBox` is a fixed absolute path** (`C:/Users/Yang/Box Sync/...`) and is *not* derived automatically, since the Box Sync folder lives in a completely separate tree unrelated to where the script sits. Update this path directly in the script if the Box Sync location changes or the script is run under a different Windows user.
- **`SeedDDSScripts`** (default `0`): `1` copies the DDS scripts of `DDSFileNames` into each new day's DDS folder, as before 2026-11-02; with `0` the DDS folder is still created (the GUI works in it) and the GUI snapshot still runs.
- **`DDSFileNames`** is the list of DDS scripts copied into each new day's DDS folder when `SeedDDSScripts = 1`. Add a new entry here whenever a new DDS script is introduced that should be seeded automatically.
- Only `.py` script files are copied into the DDS folder — no data files.
