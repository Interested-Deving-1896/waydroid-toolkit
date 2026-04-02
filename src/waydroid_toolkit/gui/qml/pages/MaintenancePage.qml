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
        function onRecordingSaved(path) {
            applicationWindow.showToast("Recording saved: " + path, false)
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
                    text: "Screen Record"
                    subtitle: maintenanceBridge.recording
                        ? "Recording in progress — click Stop to finish"
                        : "Record the Waydroid display to ~/Videos/Waydroid"
                    trailing: Component {
                        RowLayout {
                            spacing: 8
                            SpinBox {
                                id: durationSpin
                                from: 5
                                to: 300
                                value: 60
                                visible: !maintenanceBridge.recording
                                ToolTip.text: "Max duration (seconds)"
                                ToolTip.visible: hovered
                            }
                            Button {
                                text: maintenanceBridge.recording ? "Stop" : "Record"
                                flat: true
                                Material.accent: maintenanceBridge.recording
                                    ? Material.Red : Material.Teal
                                onClicked: {
                                    if (maintenanceBridge.recording)
                                        maintenanceBridge.stopRecording()
                                    else
                                        maintenanceBridge.startRecording(durationSpin.value)
                                }
                            }
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
