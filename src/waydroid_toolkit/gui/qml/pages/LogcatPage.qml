// LogcatPage.qml — live logcat viewer with tag and level filters
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    id: root
    title: "Logcat"

    readonly property int maxLines: 3000
    readonly property var levels: ["", "V", "D", "I", "W", "E", "F"]
    readonly property var levelLabels: ["All", "Verbose", "Debug", "Info", "Warn", "Error", "Fatal"]

    // ── Toolbar ───────────────────────────────────────────────────────────
    header: Pane {
        padding: 8
        Material.elevation: 1

        RowLayout {
            width: parent.width
            spacing: 8

            Label {
                text: "Logcat"
                font.pixelSize: 16
                font.weight: Font.Medium
            }

            // Tag filter
            TextField {
                id: tagField
                placeholderText: "Tag filter…"
                font.pixelSize: 12
                implicitWidth: 140
                onEditingFinished: logcatBridge.setTag(text)
                Keys.onReturnPressed: logcatBridge.setTag(text)
            }

            // Level filter
            ComboBox {
                id: levelCombo
                model: root.levelLabels
                implicitWidth: 110
                font.pixelSize: 12
                onActivated: logcatBridge.setLevel(root.levels[currentIndex])
            }

            Item { Layout.fillWidth: true }

            // Line count badge
            Label {
                text: lineCount + " lines"
                font.pixelSize: 11
                color: Material.hintTextColor
                property int lineCount: outputArea.text.split("\n").length - 1
            }

            Button {
                text: "Clear"
                flat: true
                onClicked: outputArea.text = ""
            }

            Button {
                text: logcatBridge.streaming ? "Stop" : "Start"
                flat: true
                Material.accent: logcatBridge.streaming
                    ? Material.Red : Material.Teal
                highlighted: logcatBridge.streaming
                onClicked: logcatBridge.streaming
                    ? logcatBridge.stop()
                    : logcatBridge.start()
            }
        }
    }

    // ── Output area ───────────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: "#111"

        ScrollView {
            id: scroll
            anchors.fill: parent
            anchors.margins: 6
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            TextArea {
                id: outputArea
                readOnly: true
                font.family: "monospace"
                font.pixelSize: 12
                color: "#d4d4d4"
                background: null
                wrapMode: Text.NoWrap
                selectByMouse: true
                text: ""

                onTextChanged: {
                    if (autoScrollCheck.checked) {
                        Qt.callLater(function() {
                            scroll.ScrollBar.vertical.position =
                                1.0 - scroll.ScrollBar.vertical.size
                        })
                    }
                }
            }
        }

        // Auto-scroll toggle (bottom-right corner)
        CheckBox {
            id: autoScrollCheck
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 6
            text: "Auto-scroll"
            checked: true
            font.pixelSize: 11
            opacity: 0.7
        }
    }

    // ── Bridge connections ────────────────────────────────────────────────

    Connections {
        target: logcatBridge

        function onLineReceived(line) {
            // Colour-code by level character (standard logcat format)
            var coloured = root.colouriseLine(line)

            // Trim buffer
            var lines = outputArea.text.split("\n")
            if (lines.length > root.maxLines) {
                lines = lines.slice(lines.length - root.maxLines)
                outputArea.text = lines.join("\n")
            }
            outputArea.text += coloured + "\n"
        }

        function onErrorOccurred(msg) {
            outputArea.text += "\n[Error: " + msg + "]\n"
        }

        function onStreamingChanged() {
            if (!logcatBridge.streaming && outputArea.text !== "") {
                outputArea.text += "[Stream stopped]\n"
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    // Wrap a logcat line in a colour span based on the level token.
    // Standard format: "MM-DD HH:MM:SS.mmm  PID  TID LEVEL tag: msg"
    // The level is the 5th whitespace-delimited token (index 4).
    function colouriseLine(line) {
        var parts = line.split(/\s+/)
        if (parts.length < 5) return line
        var lvl = parts[4].toUpperCase()
        // Return plain text — QML TextArea doesn't support rich text in
        // readOnly mode without a TextEdit + textFormat:RichText, which
        // has poor performance for large buffers. Prefix with a marker
        // character so users can visually scan levels.
        var prefix = ""
        if      (lvl === "E" || lvl === "F") prefix = "✖ "
        else if (lvl === "W")                prefix = "⚠ "
        else if (lvl === "I")                prefix = "  "
        else                                 prefix = "  "
        return prefix + line
    }

    // Auto-start when the page becomes visible
    Component.onCompleted: logcatBridge.start()
    Component.onDestruction: logcatBridge.stop()
}
