# 4d-plugin-log-event

Log Event writes entries to, and manages the source configuration for, the **Windows Event Log**, driving it through the same Win32 API a native C/C++ program would use (`RegisterEventSource`, `ReportEvent`, and the registry keys under `...\eventlog\Application\` that tell Event Viewer where to find your message-formatting resources). It exposes four commands: writing a log entry, registering a new event source in the registry, opening the log handle a given source writes through, and reading back which server/source the plugin is currently pointed at. All results are plain `Longint` status codes or `Text` — the plugin has no `Picture`/`Blob` return values of its own.

| Command | Returns | Purpose |
|---|---|---|
| [LOG WRITE ENTRY](#log-write-entry) | Longint (`ErrorCode`) | Writes one entry to the Windows Event Log |
| [LOG REGISTER SOURCE](#log-register-source) | — | Registers a new event source under `HKEY_LOCAL_MACHINE` |
| [LOG SET SOURCE](#log-set-source) | Longint (`ErrorCode`) | Opens the log handle a given source/server writes through |
| [LOG GET SOURCE](#log-get-source) | Text ; Text | Returns the server/source the plugin is currently using |

**Platforms:** Windows only. All four commands compile and can be called on macOS without error, but on macOS none of them do anything — see each command's Description below.

---

## Requirements & platform notes

- **Windows only, functionally.** The plugin's actual Event Log logic lives entirely inside `#if VERSIONWIN` blocks. On macOS every command is a complete no-op: `LOG WRITE ENTRY` and `LOG SET SOURCE` always return `ErrorCode` `0`, `LOG REGISTER SOURCE` does nothing, and `LOG GET SOURCE` always returns two empty strings. There's no partial/degraded macOS behavior to work around — just no behavior.
- **A default source is already active before your code runs.** On Windows, the plugin calls the equivalent of `LOG SET SOURCE("" ; "4D Application")` automatically at process startup. You only need to call `LOG SET SOURCE` yourself if you want entries to go through a different, previously-registered source.
- **`LOG REGISTER SOURCE` requires Administrator / `HKEY_LOCAL_MACHINE` write privileges.** It's a one-time setup step (typically run from an installer or an admin-run method), not something to call before every write.
- **The log handle is shared plugin-wide, not per-process.** If one 4D process calls `LOG SET SOURCE`, every other process's subsequent `LOG WRITE ENTRY` calls start going through that same source/server, until something calls `LOG SET SOURCE` again.
- **No command here returns a `Picture` or `Blob`.** Results are limited to a `Longint` error code (`0` = success) or plain `Text`.

---

## LOG WRITE ENTRY

### Syntax

```
LOG WRITE ENTRY ( Type ; Category ; EventID ; Params ; Data { ; ErrorCode } )
```

| Parameter | Type | Description |
|---|---|---|
| `Type` | Longint | Windows event type constant: `EVENTLOG_ERROR_TYPE`, `EVENTLOG_WARNING_TYPE`, `EVENTLOG_INFORMATION_TYPE`, `EVENTLOG_AUDIT_SUCCESS`, or `EVENTLOG_AUDIT_FAILURE`. Passed straight through to `ReportEvent`'s `wType`. |
| `Category` | Longint | Event category ID. Should match one of the categories your message file defines (see `CategoryCount` under [LOG REGISTER SOURCE](#log-register-source)). |
| `EventID` | Longint | Numeric event ID — this indexes into your message file's string table to pick the message template shown in Event Viewer. |
| `Params` | Array Text | One-dimensional text array. Each element is substituted, in order, into the `%1`, `%2`, ... placeholders of the `EventID`'s message template. Pass a 0-element array if the template has none. |
| `Data` | BLOB | Optional raw binary payload attached to the entry (visible in Event Viewer's Details tab). Pass an empty `BLOB` if there's nothing to attach. |
| `ErrorCode` | Longint | Result. `0` on success. On Windows, if the write fails, this holds the Win32 error code from `GetLastError`. Can be omitted if you don't need it. |

### Description

Writes one entry through whichever source is currently active (see [LOG SET SOURCE](#log-set-source)). If no source has ever been successfully opened, the command is a silent no-op — `ErrorCode` comes back `0` even though nothing was written, since there's no separate "not registered" status. In practice this only matters if the plugin's own startup registration failed for some reason, since a default source ("4D Application") is opened automatically before any of your code runs.

**On macOS**, this command always returns `ErrorCode` `0` and never touches the system, since there's no Windows Event Log to write to.

### Example

From the plugin's own test method (`Method2.4dm`):

```4d
//%attributes = {}
//using native command; the category is #0 and the event-is is #8
LOG EVENT:C667(Into Windows log events:K38:4; "some message"; Information message:K38:1)

//using plugin; by default, the source name is "4D Application"
LOG GET SOURCE($serverName; $souceName)

//these values with be inserted in the "%n" placeholders  in the message
ARRAY TEXT:C222($params; 2)
$params{1}:="arg1"
$params{2}:="arg2"

//you can attach a binary to a message
C_BLOB:C604($data)

$category:=0
$event:=2  //the database %1 has been successfully started
LOG WRITE ENTRY(EVENTLOG_ERROR_TYPE; $category; $event; $params; $data)

$category:=0
$params{1}:="oops"
$event:=5  //%1
LOG WRITE ENTRY(EVENTLOG_ERROR_TYPE; $category; $event; $params; $data)
```

A minimal write with no placeholders or attachment, capturing the error code:

```4d
ARRAY TEXT($params; 0)
C_BLOB($data)
$errorCode:=0
LOG WRITE ENTRY(EVENTLOG_INFORMATION_TYPE; 0; 1; $params; $data; $errorCode)
If ($errorCode#0)
  ALERT("Could not write to the event log: error "+String($errorCode))
End if 
```

---

## LOG REGISTER SOURCE

### Syntax

```
LOG REGISTER SOURCE ( SourceName ; CategoryCount ; MessageFilePath ; TypesSupported )
```

| Parameter | Type | Description |
|---|---|---|
| `SourceName` | Text | Name that will appear as the event source for entries written through it, and the registry subkey created under `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\services\eventlog\Application\`. If empty, the command does nothing. |
| `CategoryCount` | Longint | Number of categories your message file defines. Written verbatim to the source's `CategoryCount` registry value. |
| `MessageFilePath` | Text | Full path to the compiled message-resource file (a `.dll` built from a `.mc` message-text source) supplying the format strings for your event/category IDs. This plugin points `CategoryMessageFile`, `EventMessageFile`, and `ParameterMessageFile` all at this same path. |
| `TypesSupported` | Longint | Bitmask of event types this source can raise — combine `EVENTLOG_ERROR_TYPE`, `EVENTLOG_WARNING_TYPE`, `EVENTLOG_INFORMATION_TYPE`, `EVENTLOG_AUDIT_SUCCESS`, `EVENTLOG_AUDIT_FAILURE` with `|`. Written verbatim to `TypesSupported`. |
| Result | — | **None.** This command has no output parameter — a registry-write failure (e.g. insufficient privileges) is never reported back to your 4D code. |

### Description

Creates or overwrites the registry entries under `...\eventlog\Application\<SourceName>` that tell the Windows Event Log service where to find your message templates and what event types/categories this source supports. **Requires Administrator / `HKEY_LOCAL_MACHINE` write privileges** — run this from an install script or an admin-elevated context, not as part of ordinary application logic. Since there's no `ErrorCode` output, if you need to confirm it worked, check the registry key directly (or run the calling method elevated and trust it).

**On macOS**, this command does nothing (no registry, no Windows Event Log).

### Example

From the plugin's own test method (`Method1.4dm`) — registers a custom source, switches to it, then writes nine entries in a loop:

```4d
//%attributes = {}
//requires admin privileges
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"windows"+Folder separator:K24:12+"4dmsg-clone.dll"
$count_categories:=0
LOG REGISTER SOURCE("Custom 4D Application"; $count_categories; $path; \
EVENTLOG_WARNING_TYPE\
 | EVENTLOG_ERROR_TYPE\
 | EVENTLOG_INFORMATION_TYPE\
 | EVENTLOG_AUDIT_FAILURE\
 | EVENTLOG_AUDIT_SUCCESS)

//  //use this source
LOG SET SOURCE(""; "Custom 4D Application")

ARRAY TEXT:C222($params; 1)
$params{1}:="ì˙ñ{åÍÇÃÉÅÉbÉZÅ[ÉW"

//you can attach a binary to a message
C_BLOB:C604($data)

For ($event; 1; 9)
  LOG WRITE ENTRY(EVENTLOG_INFORMATION_TYPE; $category; $event; $params; $data)
End for 
```

(The `$params{1}` literal above is reproduced exactly as it appears in the sample file; it looks like text saved in a non-UTF-8 encoding and reads as mojibake in a UTF-8 editor — that's an artifact of the sample, not something to copy.)

---

## LOG SET SOURCE

### Syntax

```
LOG SET SOURCE ( ServerName ; SourceName { ; ErrorCode } )
```

| Parameter | Type | Description |
|---|---|---|
| `ServerName` | Text | UNC name of the remote machine to write to (e.g. `"\\SERVER01"`). Pass an empty string for the local computer — the plugin passes `NULL` to `RegisterEventSource` in that case. |
| `SourceName` | Text | Event source to open. Normally a source you registered via [LOG REGISTER SOURCE](#log-register-source), though see the caveat below. |
| `ErrorCode` | Longint | Result. `0` on success; otherwise the Win32 error code from `GetLastError`. Can be omitted if you don't need it. |

### Description

Opens a new Event Log handle for the given source/server, closing whichever handle was previously open (including the plugin's own automatic startup handle) first. Only one source/server is active at a time, and it's shared by the whole plugin instance across every 4D process — see [Requirements & platform notes](#requirements--platform-notes).

Windows itself doesn't validate `SourceName` against the registry at this point: `RegisterEventSource` still returns a valid handle for a name that was never registered via `LOG REGISTER SOURCE`. You won't get an error from `LOG SET SOURCE` in that case — instead, entries subsequently written through it will show up in Event Viewer as raw, unformatted text instead of your message file's formatted templates, because there's no registry entry pointing Event Viewer at your message file.

**On macOS**, this command always returns `ErrorCode` `0` and has no effect.

### Example

From the plugin's own test method (`Method1.4dm`), switching to a locally registered custom source:

```4d
LOG SET SOURCE(""; "Custom 4D Application")
```

Opening a source on a remote machine and checking the result:

```4d
$errorCode:=0
LOG SET SOURCE("\\LOGSERVER01"; "My Application"; $errorCode)
If ($errorCode#0)
  ALERT("Could not open the event log on \\LOGSERVER01: error "+String($errorCode))
End if 
```

---

## LOG GET SOURCE

### Syntax

```
LOG GET SOURCE ( ServerName ; SourceName )
```

| Parameter | Type | Description |
|---|---|---|
| `ServerName` | Text | Result. The server name last passed to [LOG SET SOURCE](#log-set-source) — empty for the local computer, or if `LOG SET SOURCE` has never been called explicitly. |
| `SourceName` | Text | Result. The source name last passed to [LOG SET SOURCE](#log-set-source), or `"4D Application"` if the plugin's own startup call is still the last one that ran. |

### Description

Reads back the server/source the plugin currently has open — it doesn't query Windows itself, just the plugin's own internal state. By default (no explicit `LOG SET SOURCE` call yet), this returns `("", "4D Application")`, reflecting the plugin's automatic startup registration.

**On macOS**, both values are always empty strings, since the plugin never opens any source there.

### Example

From the plugin's own test method (`Method2.4dm`):

```4d
//using plugin; by default, the source name is "4D Application"
LOG GET SOURCE($serverName; $souceName)
```

(Note: `$souceName` is spelled that way in the original sample — reproduced verbatim; use whatever variable name you like in your own code.)

---

## Error handling & troubleshooting

- **`LOG WRITE ENTRY` fails silently if no source is open.** There's no distinct "no source" error — `ErrorCode` comes back `0` either way. This only comes up if the plugin's own automatic startup registration didn't succeed, since a default source is opened before any of your code runs.
- **`LOG REGISTER SOURCE` never reports failure.** It has no output parameter at all — a permissions error writing to `HKEY_LOCAL_MACHINE` is invisible to your 4D code. Verify the registry directly, or make sure the calling context is elevated.
- **An unregistered `SourceName` in `LOG SET SOURCE` still "succeeds."** You'll get `ErrorCode` `0` and a valid handle even for a source with no registry entry — the failure mode shows up later, as unformatted raw text in Event Viewer instead of your message file's templates, not as an error here.
- **`Category`/`EventID` should match your message file.** These aren't validated by the plugin — if they don't correspond to entries your message file actually defines, expect to verify the result by looking at the entry in Event Viewer directly rather than via `ErrorCode`.
- **`Params` array size should match your template's placeholder count.** Pass a 0-element array if the message template has no `%n` placeholders — don't leave it undeclared.
- **`LOG REGISTER SOURCE` needs admin privileges.** Run it from an installer or an elevated context; a non-elevated call will simply fail to write the registry keys with no indication back to 4D.
- **Everything here is Windows-only.** All four commands compile and can be called on macOS, but none of them do anything there — see each command's Description above for the exact no-op behavior.

---

## Quick reference

```4d
  // one-time setup (installer / admin-elevated script)
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"windows"+Folder separator:K24:12+"MyMessages.dll"
LOG REGISTER SOURCE("My Application"; 1; $path; EVENTLOG_ERROR_TYPE | EVENTLOG_WARNING_TYPE | EVENTLOG_INFORMATION_TYPE)

  // point logging at that source
$errorCode:=0
LOG SET SOURCE(""; "My Application"; $errorCode)

  // write an entry
ARRAY TEXT($params; 1)
$params{1}:="some value"
C_BLOB($data)
$errorCode:=0
LOG WRITE ENTRY(EVENTLOG_INFORMATION_TYPE; 0; 1; $params; $data; $errorCode)

  // check what's currently active
LOG GET SOURCE($serverName; $sourceName)
```
