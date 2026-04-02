"""Extension dependency resolver.

Given a set of extension IDs to install, this module:

1. Expands the set by recursively pulling in ``requires`` dependencies.
2. Detects conflicts — if any two extensions in the resolved set declare
   each other (or a common extension) as a conflict, installation is aborted.
3. Returns a topologically sorted install order so that each extension is
   installed after all of its dependencies.

Raises
------
MissingDependencyError
    A required extension ID is not present in the registry.
ConflictError
    Two extensions in the resolved set conflict with each other.
CyclicDependencyError
    The ``requires`` graph contains a cycle.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping

from .base import Extension


# ── Exceptions ────────────────────────────────────────────────────────────────

class DependencyError(Exception):
    """Base class for all resolver errors."""


class MissingDependencyError(DependencyError):
    """A required extension is not registered."""

    def __init__(self, missing_id: str, required_by: str) -> None:
        super().__init__(
            f"Extension '{required_by}' requires '{missing_id}', "
            f"which is not in the registry."
        )
        self.missing_id = missing_id
        self.required_by = required_by


class ConflictError(DependencyError):
    """Two extensions in the install set conflict."""

    def __init__(self, ext_a: str, ext_b: str) -> None:
        super().__init__(
            f"Extensions '{ext_a}' and '{ext_b}' conflict and cannot both be installed."
        )
        self.ext_a = ext_a
        self.ext_b = ext_b


class CyclicDependencyError(DependencyError):
    """The requires graph contains a cycle."""

    def __init__(self, cycle: list[str]) -> None:
        path = " → ".join(cycle)
        super().__init__(f"Cyclic dependency detected: {path}")
        self.cycle = cycle


# ── Core resolver ─────────────────────────────────────────────────────────────

def resolve(
    requested: list[str],
    registry: Mapping[str, Extension],
) -> list[str]:
    """Return a topologically sorted install order for *requested* extensions.

    Parameters
    ----------
    requested:
        Extension IDs explicitly requested by the caller.
    registry:
        Mapping of id → Extension (typically ``REGISTRY`` from registry.py).

    Returns
    -------
    list[str]
        Extension IDs in dependency-first order, with all transitive
        dependencies included.

    Raises
    ------
    MissingDependencyError, ConflictError, CyclicDependencyError
    """
    # 1. Expand the full dependency set (BFS)
    full_set: set[str] = set()
    queue: deque[tuple[str, str | None]] = deque(
        (ext_id, None) for ext_id in requested
    )
    while queue:
        ext_id, required_by = queue.popleft()
        if ext_id in full_set:
            continue
        if ext_id not in registry:
            if required_by is None:
                raise MissingDependencyError(ext_id, "<requested>")
            raise MissingDependencyError(ext_id, required_by)
        full_set.add(ext_id)
        for dep in registry[ext_id].meta.requires:
            queue.append((dep, ext_id))

    # 2. Conflict detection
    for ext_id in full_set:
        for conflict_id in registry[ext_id].meta.conflicts:
            if conflict_id in full_set:
                raise ConflictError(ext_id, conflict_id)

    # 3. Topological sort (Kahn's algorithm)
    in_degree: dict[str, int] = {ext_id: 0 for ext_id in full_set}
    dependents: dict[str, list[str]] = {ext_id: [] for ext_id in full_set}

    for ext_id in full_set:
        for dep in registry[ext_id].meta.requires:
            if dep in full_set:
                in_degree[ext_id] += 1
                dependents[dep].append(ext_id)

    ready: deque[str] = deque(
        ext_id for ext_id, deg in in_degree.items() if deg == 0
    )
    order: list[str] = []

    while ready:
        # Sort for deterministic output when multiple nodes are ready
        current = sorted(ready)[0]
        ready.remove(current)
        order.append(current)
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                ready.append(dependent)

    if len(order) != len(full_set):
        # Cycle exists — find it for a useful error message
        remaining = full_set - set(order)
        cycle = _find_cycle(remaining, registry)
        raise CyclicDependencyError(cycle)

    return order


def install_with_deps(
    requested: list[str],
    registry: Mapping[str, Extension],
    progress: Callable[[str], None] | None = None,
) -> list[str]:
    """Resolve dependencies and install all extensions in order.

    Parameters
    ----------
    requested:
        Extension IDs to install (dependencies are pulled in automatically).
    registry:
        Extension registry mapping.
    progress:
        Optional callback for status messages.

    Returns
    -------
    list[str]
        IDs of extensions that were actually installed (skips already-installed).
    """
    order = resolve(requested, registry)
    installed: list[str] = []

    for ext_id in order:
        ext = registry[ext_id]
        if ext.is_installed():
            if progress:
                progress(f"[skip] {ext.meta.name} — already installed")
            continue
        if progress:
            progress(f"[install] {ext.meta.name}")
        ext.install(progress=progress)
        installed.append(ext_id)

    return installed


# ── Cycle detection helper ────────────────────────────────────────────────────

def _find_cycle(nodes: set[str], registry: Mapping[str, Extension]) -> list[str]:
    """Return a cycle path from *nodes* using DFS. Returns best-effort path."""
    visited: set[str] = set()
    stack: list[str] = []

    def _dfs(node: str) -> bool:
        if node in stack:
            idx = stack.index(node)
            stack.append(node)  # close the cycle for display
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.append(node)
        for dep in registry[node].meta.requires:
            if dep in nodes and _dfs(dep):
                return True
        stack.pop()
        return False

    for node in sorted(nodes):
        if node not in visited:
            stack.clear()
            if _dfs(node):
                # Extract just the cycle portion
                cycle_start = stack[-1]
                idx = stack.index(cycle_start)
                return stack[idx:]

    return list(nodes)  # fallback
