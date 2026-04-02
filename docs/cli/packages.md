# wdt packages

Install Android packages and manage F-Droid repositories.

## Commands

### `install`

```bash
wdt packages install /path/to/app.apk
wdt packages install https://example.com/app.apk
```

### `remove`

```bash
wdt packages remove com.example.app
```

### `list`

```bash
wdt packages list
```

### `repo add`

```bash
wdt packages repo add fdroid https://f-droid.org/repo
wdt packages repo add izzy https://apt.izzysoft.de/fdroid/repo
```

### `repo list`

```bash
wdt packages repo list
```

### `repo remove`

```bash
wdt packages repo remove fdroid
```
