// ImagesPage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Images"

    Component.onCompleted: imagesBridge.refresh()

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

            BusyOverlay { running: imagesBridge.busy }
        }
    }
}
