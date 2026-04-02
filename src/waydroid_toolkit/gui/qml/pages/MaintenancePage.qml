// MaintenancePage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Maintenance"

    Connections {
        target: maintenanceBridge
        function onScreenshotSaved(path) {
            applicationWindow.showToast("Screenshot saved: " + path, false)
        }
        function onLogcatOutput(output) {
            logcatArea.text = output
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
                text: "Maintenance"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            SettingsGroup {
                title: "Tools"
                Layout.fillWidth: true

                ActionRow {
                    text: "Screenshot"
                    subtitle: "Capture the current Waydroid display"
                    trailing: Component {
                        Button {
                            text: "Capture"
                            flat: true
                            Material.accent: Material.Teal
                            onClicked: maintenanceBridge.captureScreenshot()
                        }
                    }
                }

                ActionRow {
                    text: "Logcat"
                    subtitle: "Fetch recent Android log output"
                    trailing: Component {
                        Button {
                            text: "Fetch"
                            flat: true
                            Material.accent: Material.Teal
                            onClicked: maintenanceBridge.startLogcat()
                        }
                    }
                }
            }

            // Logcat output
            SettingsGroup {
                title: "Log output"
                Layout.fillWidth: true
                visible: logcatArea.text !== ""

                ScrollView {
                    width: parent.width
                    height: 300
                    clip: true

                    TextArea {
                        id: logcatArea
                        readOnly: true
                        font.family: "monospace"
                        font.pixelSize: 12
                        wrapMode: Text.NoWrap
                        background: null
                    }
                }
            }

            BusyOverlay { running: maintenanceBridge.busy }
        }
    }
}
