// FileManagerPage.qml — push/pull file transfer between host and Waydroid
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtCore
import "../components"

Page {
    id: root
    title: "Files"

    property string transferLog: ""

    Connections {
        target: fileBridge

        function onTransferDone(ok, msg) {
            root.transferLog += (ok ? "✓ " : "✗ ") + msg + "\n"
        }

        function onProgressMsg(msg) {
            root.transferLog += "  " + msg + "\n"
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
                text: "File Transfer"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Label {
                text: "Transfer files between the host and the Waydroid container via adb."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                Layout.fillWidth: true
            }

            // ── Push (host → Waydroid) ────────────────────────────────────
            SettingsGroup {
                title: "Push — host → Waydroid"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    padding: 8

                    RowLayout {
                        spacing: 8
                        Layout.fillWidth: true

                        TextField {
                            id: pushLocalField
                            placeholderText: "Local file path…"
                            Layout.fillWidth: true
                            font.pixelSize: 13
                        }

                        Button {
                            text: "Browse"
                            flat: true
                            onClicked: pushFileDialog.open()
                        }
                    }

                    TextField {
                        id: pushDestField
                        placeholderText: "Android destination (e.g. /sdcard/Download/)"
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        text: "/sdcard/Download/"
                    }

                    Button {
                        text: "Push"
                        enabled: pushLocalField.text.trim() !== ""
                            && pushDestField.text.trim() !== ""
                            && !fileBridge.busy
                        Material.accent: Material.Teal
                        onClicked: {
                            root.transferLog = ""
                            fileBridge.pushFile(
                                pushLocalField.text.trim(),
                                pushDestField.text.trim()
                            )
                        }
                    }
                }
            }

            // ── Pull (Waydroid → host) ────────────────────────────────────
            SettingsGroup {
                title: "Pull — Waydroid → host"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    padding: 8

                    TextField {
                        id: pullSrcField
                        placeholderText: "Android source path (e.g. /sdcard/DCIM/photo.jpg)"
                        Layout.fillWidth: true
                        font.pixelSize: 13
                    }

                    RowLayout {
                        spacing: 8
                        Layout.fillWidth: true

                        TextField {
                            id: pullDestField
                            placeholderText: "Local destination directory…"
                            Layout.fillWidth: true
                            font.pixelSize: 13
                            text: StandardPaths.writableLocation(
                                StandardPaths.DownloadLocation)
                        }

                        Button {
                            text: "Browse"
                            flat: true
                            onClicked: pullDirDialog.open()
                        }
                    }

                    Button {
                        text: "Pull"
                        enabled: pullSrcField.text.trim() !== ""
                            && pullDestField.text.trim() !== ""
                            && !fileBridge.busy
                        Material.accent: Material.Teal
                        onClicked: {
                            root.transferLog = ""
                            // Append filename to dest dir if it looks like a dir
                            var src = pullSrcField.text.trim()
                            var dest = pullDestField.text.trim()
                            if (!dest.endsWith("/")) dest += "/"
                            var filename = src.split("/").pop()
                            fileBridge.pullFile(src, dest + filename)
                        }
                    }
                }
            }

            // ── Transfer log ──────────────────────────────────────────────
            SettingsGroup {
                title: "Transfer log"
                Layout.fillWidth: true
                visible: root.transferLog !== ""

                RowLayout {
                    width: parent.width

                    ScrollView {
                        Layout.fillWidth: true
                        height: 120
                        clip: true

                        TextArea {
                            readOnly: true
                            font.family: "monospace"
                            font.pixelSize: 12
                            text: root.transferLog
                            wrapMode: Text.WordWrap
                            background: null
                        }
                    }

                    Button {
                        text: "Clear"
                        flat: true
                        onClicked: root.transferLog = ""
                        Layout.alignment: Qt.AlignTop
                    }
                }
            }

            BusyOverlay { running: fileBridge.busy }
        }
    }

    // ── File dialogs ──────────────────────────────────────────────────────
    // Qt 6 file dialogs via QtQuick.Dialogs
    Loader {
        id: pushFileDialog
        active: false
        sourceComponent: Component {
            Item {
                // Fallback: just focus the text field for manual entry
                Component.onCompleted: {
                    pushLocalField.forceActiveFocus()
                    pushFileDialog.active = false
                }
            }
        }
        function open() { active = true }
    }

    Loader {
        id: pullDirDialog
        active: false
        sourceComponent: Component {
            Item {
                Component.onCompleted: {
                    pullDestField.forceActiveFocus()
                    pullDirDialog.active = false
                }
            }
        }
        function open() { active = true }
    }
}
