# wdt extensions

Manage Waydroid extensions with automatic dependency resolution and conflict detection.

## Commands

### `list`

```bash
wdt extensions list
```

Prints a table of all available extensions with their install state, conflicts, and requirements.

### `install`

```bash
wdt extensions install EXT_ID [EXT_ID ...]
wdt extensions install gapps widevine
wdt extensions install gapps --dry-run
```

Installs one or more extensions. Dependencies are pulled in automatically.
Conflicting extensions (e.g. `gapps` and `microg`) are detected before
anything is written and the command exits with an error.

`--dry-run` prints the resolved install order without installing.

### `remove`

```bash
wdt extensions remove EXT_ID
wdt extensions remove magisk
```

### `deps`

```bash
wdt extensions deps EXT_ID [EXT_ID ...]
wdt extensions deps gapps widevine
```

Shows the resolved dependency order as a table.

## Available extensions

| ID | Name | Conflicts |
|---|---|---|
| `gapps` | Google Apps (OpenGApps) | `microg` |
| `microg` | microG | `gapps` |
| `magisk` | Magisk | — |
| `libhoudini` | libhoudini (ARM translation) | `libndk` |
| `libndk` | libndk (ARM translation) | `libhoudini` |
| `widevine` | Widevine L3 DRM | — |
| `keymapper` | Key Mapper | — |

## Dependency resolution

The resolver performs a BFS expansion of all `requires` fields, then a
topological sort (Kahn's algorithm). Errors raised:

- `MissingDependencyError` — a required extension is not in the registry
- `ConflictError` — two extensions in the install set conflict
- `CyclicDependencyError` — the requires graph contains a cycle
