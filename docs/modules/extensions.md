# Extensions module

`waydroid_toolkit.modules.extensions`

## Extension base class

```python
from waydroid_toolkit.modules.extensions.base import Extension, ExtensionMeta

@dataclass
class ExtensionMeta:
    id: str
    name: str
    description: str
    requires_root: bool = True
    conflicts: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
```

All extensions implement:

```python
class Extension(ABC):
    @property
    def meta(self) -> ExtensionMeta: ...
    def is_installed(self) -> bool: ...
    def install(self, progress=None) -> None: ...
    def uninstall(self, progress=None) -> None: ...
    def state(self) -> ExtensionState: ...
```

## Registry

```python
from waydroid_toolkit.modules.extensions import REGISTRY, get, list_all

ext = get("gapps")
all_exts = list_all()
```

## Dependency resolver

```python
from waydroid_toolkit.modules.extensions import resolve, install_with_deps

# Resolve install order (raises on conflict or cycle)
order = resolve(["gapps", "widevine"], REGISTRY)

# Install with deps, skipping already-installed
installed = install_with_deps(["gapps"], REGISTRY, progress=print)
```

### Exceptions

| Exception | Raised when |
|---|---|
| `MissingDependencyError` | A required extension is not in the registry |
| `ConflictError` | Two extensions in the set conflict |
| `CyclicDependencyError` | The requires graph has a cycle |

## Adding a new extension

1. Create `src/waydroid_toolkit/modules/extensions/myext.py` implementing `Extension`.
2. Add an entry to `REGISTRY` in `registry.py`.
3. Export from `__init__.py` if needed.
4. Add tests in `tests/unit/test_myext.py`.
