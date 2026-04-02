// ImagesPage.qml — image profile management + OTA update checker
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtCore
import "../components"

Page {
    id: root
    title: "Images"

    // OTA state
    property var updateRows: []       // [{channel, current, latest, available}]
    property bool otaChecked: false
    property string downloadLog: ""

    Component.onCompleted: imagesBridge.refresh()

    // ── Bridge connections ────────────────────────────────────────────────
    Connections {
        target: imagesBridge

        function onUpdateInfoReady(rows) {
            root.updateRows = rows
            root.otaChecked = true
        }

        function onDownloadProgress(msg) {
            root.downloadLog += msg + "\n"
        }

        function onDownloadDone(ok, msg) {
            root.downloadLog += (ok ? "✓ " : "✗ ") + msg + "\n"
            // Refresh profile list in case new images were staged
            imagesBridge.refresh()
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            padding: 24

            Label {
                text: "Image Profiles"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Label {
                text: "Manage Waydroid image profiles. The active profile is used on next session start."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                Layout.fillWidth: true
            }

            // ── Profiles ──────────────────────────────────────────────────
            SettingsGroup {
                title: "Profiles"
                Layout.fillWidth: true

                Repeater {
                    model: imagesBridge.images

                    ActionRow {
                        text: modelData.name
                        subtitle: modelData.active ? "Active" : ""
                        trailing: Component {
                            Button {
                                text: "Activate"
                                flat: true
                                enabled: !modelData.active
                                Material.accent: Material.Teal
                                onClicked: imagesBridge.activate(modelData.name)
                            }
                        }
                    }
                }
            }

            // ── OTA update checker ────────────────────────────────────────
            SettingsGroup {
                title: "OTA Updates"
                Layout.fillWidth: true

                // Check button row
                ActionRow {
                    text: "Check for updates"
                    subtitle: "Compare installed images against the OTA channel"
                    trailing: Component {
                        Button {
                            text: "Check"
                            flat: true
                            Material.accent: Material.Teal
                            enabled: !imagesBridge.busy
                            onClicked: {
                                root.otaChecked = false
                                root.updateRows = []
                                imagesBridge.checkUpdate()
                            }
                        }
                    }
                }

                // Results table — shown after a check
                ColumnLayout {
                    visible: root.otaChecked
                    width: parent.width
                    spacing: 0

                    Repeater {
                        model: root.updateRows

                        delegate: Pane {
                            Layout.fillWidth: true
                            padding: 12
                            background: Rectangle {
                                color: index % 2 === 0
                                    ? Material.color(Material.Grey, Material.Shade50)
                                    : "transparent"
                            }

                            RowLayout {
                                width: parent.width
                                spacing: 12

                                Label {
                                    text: modelData.channel
                                    font.weight: Font.Medium
                                    font.capitalization: Font.Capitalize
                                    implicitWidth: 60
                                }
                                Label {
                                    text: "current: " + modelData.current
                                    font.pixelSize: 12
                                    color: Material.hintTextColor
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: "latest: " + modelData.latest
                                    font.pixelSize: 12
                                    color: Material.hintTextColor
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: modelData.available ? "update available" : "up to date"
                                    font.pixelSize: 12
                                    color: modelData.available
                                        ? Material.color(Material.Green)
                                        : Material.hintTextColor
                                }
                            }
                        }
                    }
                }

                // Download button — shown when at least one update is available
                ActionRow {
                    visible: root.otaChecked && root.updateRows.some(
                        function(r) { return r.available })
                    text: "Download updates"
                    subtitle: "Save to ~/waydroid-images/ota"
                    trailing: Component {
                        Button {
                            text: "Download"
                            flat: true
                            Material.accent: Material.Teal
                            enabled: !imagesBridge.busy
                            onClicked: {
                                root.downloadLog = ""
                                var dest = StandardPaths.writableLocation(
                                    StandardPaths.HomeLocation) + "/waydroid-images/ota"
                                imagesBridge.downloadImages(dest)
                            }
                        }
                    }
                }
            }

            // ── Download log ──────────────────────────────────────────────
            SettingsGroup {
                title: "Download log"
                Layout.fillWidth: true
                visible: root.downloadLog !== ""

                ScrollView {
                    width: parent.width
                    height: 160
                    clip: true

                    TextArea {
                        readOnly: true
                        font.family: "monospace"
                        font.pixelSize: 12
                        text: root.downloadLog
                        wrapMode: Text.WordWrap
                        background: null
                    }
                }
            }

            BusyOverlay { running: imagesBridge.busy }
        }
    }
}
