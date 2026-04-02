// BusyOverlay.qml — full-page busy indicator
import QtQuick
import QtQuick.Controls.Material

Item {
    id: root
    property bool running: false
    visible: running
    anchors.fill: parent
    z: 100

    Rectangle {
        anchors.fill: parent
        color: Material.background
        opacity: 0.6
    }

    BusyIndicator {
        anchors.centerIn: parent
        running: root.running
    }
}
