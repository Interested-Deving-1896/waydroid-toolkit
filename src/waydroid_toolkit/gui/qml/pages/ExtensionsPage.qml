// ExtensionsPage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Extensions"

    Component.onCompleted: extensionsBridge.refresh()

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            padding: 24

            Label {
                text: "Extensions"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Label {
                text: "Install optional extensions into the Waydroid overlay. Requires root and an active session."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                Layout.fillWidth: true
            }

            SettingsGroup {
                title: "Available extensions"
                Layout.fillWidth: true

                Repeater {
                    model: extensionsBridge.extensions

                    ActionRow {
                        text: modelData.name
                        subtitle: modelData.description
                        trailing: Component {
                            RowLayout {
                                spacing: 8

                                Label {
                                    text: modelData.installed ? "Installed" : ""
                                    color: Material.color(Material.Green)
                                    font.pixelSize: 12
                                    visible: modelData.installed
                                }

                                Button {
                                    text: modelData.installed ? "Remove" : "Install"
                                    flat: true
                                    Material.accent: modelData.installed
                                                     ? Material.Red : Material.Teal
                                    onClicked: {
                                        if (modelData.installed)
                                            extensionsBridge.uninstall(modelData.id)
                                        else
                                            extensionsBridge.install(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            BusyOverlay { running: extensionsBridge.busy }
        }
    }
}
