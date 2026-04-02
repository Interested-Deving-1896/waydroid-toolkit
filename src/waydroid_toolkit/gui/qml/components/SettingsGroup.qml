// SettingsGroup.qml — labelled group box for settings rows
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Column {
    id: root

    property string title: ""
    default property alias content: container.data

    spacing: 0
    width: parent ? parent.width : 0

    Label {
        text: root.title
        font.pixelSize: 12
        font.weight: Font.Medium
        color: Material.accent
        leftPadding: 16
        bottomPadding: 4
        visible: root.title !== ""
    }

    Pane {
        width: parent.width
        padding: 0
        Material.elevation: 1

        background: Rectangle {
            color: Material.background
            radius: 8
            border.color: Material.dividerColor
            border.width: 1
        }

        Column {
            id: container
            width: parent.width
            spacing: 0
        }
    }
}
