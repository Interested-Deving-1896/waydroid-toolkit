// BackupPage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Page {
    title: "Backup"

    Connections {
        target: backupBridge
        function onBackupDone(path) {
            applicationWindow.showToast("Backup saved: " + path, false)
        }
        function onRestoreDone() {
            applicationWindow.showToast("Restore complete. Restart Waydroid to apply.", false)
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
                text: "Backup & Restore"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            SettingsGroup {
                title: "Backup"
                Layout.fillWidth: true

                ActionRow {
                    text: "Create backup"
                    subtitle: "Archive Waydroid data to a .tar.gz file"
                    trailing: Component {
                        Button {
                            text: "Backup…"
                            flat: true
                            Material.accent: Material.Teal
                            onClicked: backupDirPicker.open()
                        }
                    }
                }
            }

            SettingsGroup {
                title: "Restore"
                Layout.fillWidth: true

                ActionRow {
                    text: "Restore from backup"
                    subtitle: "Overwrite current Waydroid data from a backup archive"
                    trailing: Component {
                        Button {
                            text: "Restore…"
                            flat: true
                            Material.accent: Material.Orange
                            onClicked: restorePicker.open()
                        }
                    }
                }
            }

            BusyOverlay { running: backupBridge.busy }
        }
    }

    FolderDialog {
        id: backupDirPicker
        title: "Select backup destination"
        onAccepted: backupBridge.backup(selectedFolder.toString().replace("file://", ""))
    }

    FileDialog {
        id: restorePicker
        title: "Select backup archive"
        nameFilters: ["Archives (*.tar.gz *.tgz)"]
        onAccepted: backupBridge.restore(selectedFile.toString().replace("file://", ""))
    }
}
