// WdtToast.qml — Material-style toast notification
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Popup {
    id: root

    property string message: ""
    property bool isError: false

    anchors.centerIn: parent
    width: Math.min(messageLabel.implicitWidth + 48, parent.width - 48)
    height: messageLabel.implicitHeight + 24
    modal: false
    focus: false
    closePolicy: Popup.NoAutoClose

    background: Rectangle {
        radius: 6
        color: root.isError ? Material.color(Material.Red, Material.Shade700)
                            : Material.color(Material.Grey, Material.Shade800)
    }

    contentItem: Label {
        id: messageLabel
        text: root.message
        color: "white"
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }

    Timer {
        id: dismissTimer
        interval: root.isError ? 5000 : 3000
        onTriggered: root.close()
    }

    onOpened: dismissTimer.restart()

    function show(msg, error) {
        root.message = msg
        root.isError = error === true
        root.open()
    }
}
