"""Packages page — Qt Widgets QTableView for package search results.

This page is embedded into the QML PackagesPage via QQuickWidget.
It provides a sortable, filterable QTableView backed by a QStandardItemModel
for displaying F-Droid search results — a use case where Qt's model/view
architecture is more appropriate than a QML ListView.
"""

from __future__ import annotations

from waydroid_toolkit.gui.pages.base import WdtPage
from waydroid_toolkit.gui.qt_compat import QtCore, QtWidgets


class PackageTableModel(QtCore.QAbstractTableModel):
    """Model for F-Droid package search results."""

    HEADERS = ["Name", "Package ID"]

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._data: list[dict] = []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid() or role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        row = self._data[index.row()]
        if index.column() == 0:
            return row.get("name", "")
        return row.get("packageName", "")

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self.HEADERS[section]
        return None

    def set_packages(self, packages: list[dict]) -> None:
        self.beginResetModel()
        self._data = packages
        self.endResetModel()

    def package_at(self, row: int) -> dict:
        return self._data[row] if 0 <= row < len(self._data) else {}


class PackagesWidget(WdtPage):
    """Qt Widgets package browser with sortable QTableView."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            title="Packages",
            subtitle="Search F-Droid repositories and install APKs.",
            parent=parent,
        )
        self._build_packages_ui()

    def _build_packages_ui(self) -> None:
        # Search bar
        search_row = QtWidgets.QHBoxLayout()
        self._search_field = QtWidgets.QLineEdit()
        self._search_field.setPlaceholderText("Search F-Droid repos…")
        self._search_field.returnPressed.connect(self._on_search)
        search_btn = QtWidgets.QPushButton("Search")
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self._search_field)
        search_row.addWidget(search_btn)
        self.content_layout.addLayout(search_row)

        # Table
        self._model = PackageTableModel()
        self._proxy = QtCore.QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)  # filter all columns

        self._table = QtWidgets.QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_install)
        self.content_layout.addWidget(self._table)

        # Filter bar
        filter_row = QtWidgets.QHBoxLayout()
        filter_lbl = QtWidgets.QLabel("Filter:")
        self._filter_field = QtWidgets.QLineEdit()
        self._filter_field.setPlaceholderText("Filter results…")
        self._filter_field.textChanged.connect(self._proxy.setFilterFixedString)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self._filter_field)
        self.content_layout.addLayout(filter_row)

        # Install button
        install_btn = QtWidgets.QPushButton("Install selected")
        install_btn.clicked.connect(self._on_install_selected)
        self.content_layout.addWidget(install_btn)

    def _on_search(self) -> None:
        query = self._search_field.text().strip()
        if not query:
            return

        def _search() -> list:
            from waydroid_toolkit.modules.packages.manager import search_repos
            return list(search_repos(query))

        self.run_async(_search, on_done=self._model.set_packages)

    def _on_install(self, index: QtCore.QModelIndex) -> None:
        src_index = self._proxy.mapToSource(index)
        pkg = self._model.package_at(src_index.row())
        self._install_package(pkg)

    def _on_install_selected(self) -> None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return
        src_index = self._proxy.mapToSource(indexes[0])
        pkg = self._model.package_at(src_index.row())
        self._install_package(pkg)

    def _install_package(self, pkg: dict) -> None:
        pkg_name = pkg.get("packageName", "")
        if not pkg_name:
            return

        def _do() -> None:
            from waydroid_toolkit.modules.packages.manager import install_package
            install_package(pkg_name)

        self.run_async(
            _do,
            on_done=lambda _: self.show_toast(
                f"Installed {pkg.get('name', pkg_name)}", error=False
            ),
        )
