// ActionRow.qml — single row inside a SettingsGroup
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

ItemDelegate {
    id: root

    property string subtitle: ""
    property alias trailing: trailingLoader.sourceComponent

    width: parent ? parent.width : 0
    height: Math.max(56, contentLayout.implicitHeight + 16)
    leftPadding: 16
    rightPadding: 16

    contentItem: RowLayout {
        id: contentLayout
        spacing: 12

        Column {
            Layout.fillWidth: true
            spacing: 2

            Label {
                text: root.text
                font.pixelSize: 14
                color: Material.foreground
                width: parent.width
                elide: Text.ElideRight
            }

            Label {
                text: root.subtitle
                font.pixelSize: 12
                color: Material.hintTextColor
                visible: root.subtitle !== ""
                width: parent.width
                elide: Text.ElideRight
                wrapMode: Text.WordWrap
            }
        }

        Loader {
            id: trailingLoader
            Layout.alignment: Qt.AlignVCenter
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width - 16
        x: 16
        height: 1
        color: Material.dividerColor
        visible: parent.ListView ? parent.ListView.isCurrentItem === false : true
    }
}
