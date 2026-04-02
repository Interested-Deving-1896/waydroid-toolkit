# wdt performance

Host-side performance tuning for gaming workloads.

## Commands

### `apply`

```bash
wdt performance apply
wdt performance apply --zram-size 8192 --governor performance --turbo
```

Options:

| Option | Default | Description |
|---|---|---|
| `--zram-size MB` | `4096` | ZRAM swap size in MiB |
| `--governor NAME` | `performance` | CPU frequency governor |
| `--turbo` | off | Enable Intel Turbo Boost |
| `--gamemode` | off | Start GameMode daemon |

### `reset`

```bash
wdt performance reset
```

Reverts all tuning to system defaults.

### `status`

```bash
wdt performance status
```

Shows current governor, ZRAM size, and Turbo Boost state.
