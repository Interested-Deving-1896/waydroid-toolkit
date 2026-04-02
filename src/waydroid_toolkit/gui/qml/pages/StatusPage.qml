// StatusPage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Status"

    Connections {
        target: statusBridge
        function onStatusChanged() { busyOverlay.running = false }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            padding: 24

            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: "Waydroid Status"
                    font.pixelSize: 22
                    font.weight: Font.Medium
                    Layout.fillWidth: true
                }

                Button {
                    text: "Refresh"
                    Material.accent: Material.Teal
                    flat: true
                    onClicked: {
                        busyOverlay.running = true
                        statusBridge.refresh()
                    }
                }
            }

            SettingsGroup {
                title: "Runtime"
                Layout.fillWidth: true

                ActionRow {
                    text: "Installed"
                    subtitle: statusBridge.installed ? "Yes" : "No"
                    trailing: Component {
                        Rectangle {
                            width: 10; height: 10; radius: 5
                            color: statusBridge.installed ? Material.color(Material.Green)
                                                          : Material.color(Material.Red)
                        }
                    }
                }

                ActionRow {
                    text: "Initialised"
                    subtitle: statusBridge.initialized ? "Yes" : "No"
                    trailing: Component {
                        Rectangle {
                            width: 10; height: 10; radius: 5
                            color: statusBridge.initialized ? Material.color(Material.Green)
                                                            : Material.color(Material.Red)
                        }
                    }
                }

                ActionRow {
                    text: "Session"
                    subtitle: statusBridge.session
                }

                ActionRow {
                    text: "Active backend"
                    subtitle: statusBridge.backend !== "" ? statusBridge.backend : "—"
                }
            }

            SettingsGroup {
                title: "ADB"
                Layout.fillWidth: true

                ActionRow {
                    text: "ADB available"
                    subtitle: statusBridge.adbReady ? "Connected" : "Not connected"
                    trailing: Component {
                        Rectangle {
                            width: 10; height: 10; radius: 5
                            color: statusBridge.adbReady ? Material.color(Material.Green)
                                                         : Material.color(Material.Grey)
                        }
                    }
                }
            }

            SettingsGroup {
                title: "Storage"
                Layout.fillWidth: true

                ActionRow {
                    text: "Images path"
                    subtitle: statusBridge.imagesPath !== "" ? statusBridge.imagesPath : "—"
                }
            }
        }
    }

    BusyOverlay { id: busyOverlay }
}
