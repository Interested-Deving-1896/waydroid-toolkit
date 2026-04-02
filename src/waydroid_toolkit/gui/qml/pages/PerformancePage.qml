// PerformancePage.qml
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    title: "Performance"

    readonly property var profiles: [
        { id: "balanced",    label: "Balanced",     description: "Default system settings." },
        { id: "performance", label: "Performance",  description: "CPU governor set to performance, I/O scheduler tuned." },
        { id: "powersave",   label: "Power save",   description: "CPU governor set to powersave." },
    ]

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            padding: 24

            Label {
                text: "Performance Tuning"
                font.pixelSize: 22
                font.weight: Font.Medium
            }

            Label {
                text: "Apply host-level performance tuning for the Waydroid session. Requires root."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                Layout.fillWidth: true
            }

            SettingsGroup {
                title: "Profiles"
                Layout.fillWidth: true

                Repeater {
                    model: profiles

                    ActionRow {
                        text: modelData.label
                        subtitle: modelData.description
                        trailing: Component {
                            RadioButton {
                                checked: performanceBridge.activeProfile === modelData.id
                                onClicked: performanceBridge.applyProfile(modelData.id)
                            }
                        }
                    }
                }
            }

            BusyOverlay { running: performanceBridge.busy }
        }
    }
}
