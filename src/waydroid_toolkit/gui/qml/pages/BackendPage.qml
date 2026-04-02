// BackendPage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Backend"

    Component.onCompleted: backendBridge.refresh()

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            padding: 24

            Label {
                text: "Container Backend"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Label {
                text: "Select the container backend used to run the Waydroid session. Changes take effect on next session start."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                Layout.fillWidth: true
            }

            SettingsGroup {
                title: "Available backends"
                Layout.fillWidth: true

                Repeater {
                    model: backendBridge.backends

                    ActionRow {
                        text: modelData.id
                        subtitle: modelData.available ? "Available" : "Not installed"
                        enabled: modelData.available
                        trailing: Component {
                            RadioButton {
                                checked: backendBridge.active === modelData.id
                                enabled: modelData.available
                                onClicked: backendBridge.setActive(modelData.id)
                            }
                        }
                    }
                }
            }

            BusyOverlay { running: backendBridge.busy }
        }
    }
}
