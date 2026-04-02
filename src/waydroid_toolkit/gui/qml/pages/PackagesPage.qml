// PackagesPage.qml — search + install APKs, manage F-Droid repos
// Heavy data view (package list) is rendered by the Qt Widgets PackagesWidget
// embedded via QQuickWidget from the Python side. This QML page handles
// the search bar, repo management, and APK file picker.
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Page {
    title: "Packages"

    Component.onCompleted: packagesBridge.refreshRepos()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Toolbar ───────────────────────────────────────────────────────
        Pane {
            Layout.fillWidth: true
            padding: 12
            Material.elevation: 1

            RowLayout {
                width: parent.width
                spacing: 8

                TextField {
                    id: searchField
                    Layout.fillWidth: true
                    placeholderText: "Search F-Droid repos…"
                    onAccepted: packagesBridge.search(text)
                }

                Button {
                    text: "Search"
                    Material.accent: Material.Teal
                    onClicked: packagesBridge.search(searchField.text)
                }

                Button {
                    text: "Install APK…"
                    flat: true
                    onClicked: apkPicker.open()
                }
            }
        }

        // ── Search results ────────────────────────────────────────────────
        ListView {
            id: resultsList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: packagesBridge.packages
            visible: packagesBridge.packages.length > 0

            delegate: ItemDelegate {
                width: resultsList.width
                height: 56

                contentItem: ColumnLayout {
                    spacing: 2
                    Label {
                        text: modelData.name
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Label {
                        text: modelData.packageName
                        font.pixelSize: 12
                        color: Material.hintTextColor
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                onClicked: {
                    packagesBridge.installApk(modelData.packageName)
                    applicationWindow.showToast("Installing " + modelData.name + "…", false)
                }
            }
        }

        // ── Repo management ───────────────────────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 16
            spacing: 12
            visible: packagesBridge.packages.length === 0

            Label {
                text: "F-Droid Repositories"
                font.pixelSize: 16
                font.weight: Font.Medium
            }

            SettingsGroup {
                Layout.fillWidth: true

                Repeater {
                    model: packagesBridge.repos

                    ActionRow {
                        text: modelData.name !== "" ? modelData.name : modelData.url
                        subtitle: modelData.url
                        trailing: Component {
                            Button {
                                text: "Remove"
                                flat: true
                                Material.accent: Material.Red
                                onClicked: packagesBridge.removeRepo(modelData.url)
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                TextField {
                    id: repoUrlField
                    Layout.fillWidth: true
                    placeholderText: "https://f-droid.org/repo"
                }

                Button {
                    text: "Add repo"
                    Material.accent: Material.Teal
                    onClicked: {
                        if (repoUrlField.text !== "") {
                            packagesBridge.addRepo(repoUrlField.text)
                            repoUrlField.clear()
                        }
                    }
                }
            }
        }

        BusyOverlay { running: packagesBridge.busy }
    }

    FileDialog {
        id: apkPicker
        title: "Select APK"
        nameFilters: ["APK files (*.apk)"]
        onAccepted: packagesBridge.installApk(selectedFile.toString().replace("file://", ""))
    }
}
