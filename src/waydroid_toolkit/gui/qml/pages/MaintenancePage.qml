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
                    subtitle: "View live Android log output"
                    trailing: Component {
                        Button {
                            text: "Open"
                            flat: true
                            Material.accent: Material.Teal
                            onClicked: applicationWindow.pageStack.replace(
                                Qt.resolvedUrl("LogcatPage.qml"))
                        }
                    }
                }
            }

            BusyOverlay { running: maintenanceBridge.busy }
        }
    }
}
