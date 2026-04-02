// TerminalPage.qml
// Uses QtWebEngineQuick + wadb when available; falls back to a native
// adb shell REPL (AdbShellBridge) otherwise.
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    id: root
    title: "Terminal"

    property string wadbHtmlUrl: typeof _wadbUrl !== "undefined" ? _wadbUrl : ""
    property bool   webEngineAvailable: typeof WebEngineView !== "undefined"
    property bool   useNative: !webEngineAvailable || wadbHtmlUrl === ""

    // Maximum lines kept in the native terminal buffer
    readonly property int maxLines: 2000

    // ── Toolbar ───────────────────────────────────────────────────────────
    header: Pane {
        padding: 8
        Material.elevation: 1

        RowLayout {
            width: parent.width
            spacing: 8

            Label {
                text: "ADB Terminal"
                font.pixelSize: 16
                font.weight: Font.Medium
                Layout.fillWidth: true
            }

            Label {
                text: root.useNative ? "native adb shell" : "wadb (WebUSB)"
                font.pixelSize: 12
                color: Material.hintTextColor
            }

            // Connect / Disconnect button (native mode only)
            Button {
                visible: root.useNative
                flat: true
                Material.accent: Material.Teal
                text: adbShellBridge.connected ? "Disconnect" : "Connect"
                onClicked: adbShellBridge.connected
                    ? adbShellBridge.disconnectShell()
                    : adbShellBridge.connectShell()
            }

            // Reload button (WebEngine mode only)
            Button {
                visible: !root.useNative
                flat: true
                text: "Reload"
                Material.accent: Material.Teal
                onClicked: {
                    if (webEngineLoader.item && webEngineLoader.item.reload) {
                        webEngineLoader.item.reload()
                    }
                }
            }
        }
    }

    // ── WebEngine terminal (wadb) ─────────────────────────────────────────
    Loader {
        id: webEngineLoader
        anchors.fill: parent
        active: !root.useNative

        sourceComponent: Component {
            Item {
                anchors.fill: parent
                Component.onCompleted: {
                    var comp = Qt.createComponent("WebEngineTerminal.qml")
                    if (comp.status === Component.Ready) {
                        comp.createObject(this, {
                            anchors: { fill: this },
                            url: root.wadbHtmlUrl
                        })
                    }
                }
            }
        }
    }

    // ── Native adb shell REPL ─────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0
        visible: root.useNative

        // Status banner shown when not connected
        Pane {
            Layout.fillWidth: true
            padding: 8
            visible: !adbShellBridge.connected
            background: Rectangle {
                color: Material.color(Material.Orange, Material.Shade100)
            }

            Label {
                width: parent.width
                text: "Not connected — press Connect to open an adb shell session."
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: Material.color(Material.Orange, Material.Shade900)
            }
        }

        // Output area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1a1a1a"

            ScrollView {
                id: outputScroll
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                TextArea {
                    id: outputArea
                    readOnly: true
                    font.family: "monospace"
                    font.pixelSize: 13
                    color: "#d4d4d4"
                    background: null
                    wrapMode: Text.NoWrap
                    selectByMouse: true
                    text: "$ Press Connect to start an adb shell session.\n"

                    onTextChanged: {
                        Qt.callLater(function() {
                            outputScroll.ScrollBar.vertical.position =
                                1.0 - outputScroll.ScrollBar.vertical.size
                        })
                    }
                }
            }
        }

        // Input row
        Pane {
            Layout.fillWidth: true
            padding: 8
            Material.elevation: 2

            RowLayout {
                width: parent.width
                spacing: 8

                Label {
                    text: "$"
                    font.family: "monospace"
                    font.pixelSize: 14
                    color: adbShellBridge.connected
                        ? Material.color(Material.Teal)
                        : Material.hintTextColor
                }

                TextField {
                    id: cmdField
                    Layout.fillWidth: true
                    placeholderText: adbShellBridge.connected
                        ? "Enter command…"
                        : "Connect first…"
                    enabled: adbShellBridge.connected
                    font.family: "monospace"
                    font.pixelSize: 13
                    background: Rectangle {
                        color: "#2a2a2a"
                        radius: 4
                        border.color: cmdField.activeFocus
                            ? Material.color(Material.Teal)
                            : "#444"
                    }
                    color: "#d4d4d4"

                    Keys.onReturnPressed: root.sendCmd()
                    Keys.onEnterPressed:  root.sendCmd()

                    // Simple command history (up/down arrows)
                    property var history: []
                    property int historyIdx: -1

                    Keys.onUpPressed: {
                        if (history.length === 0) return
                        historyIdx = Math.min(historyIdx + 1, history.length - 1)
                        text = history[history.length - 1 - historyIdx]
                    }
                    Keys.onDownPressed: {
                        if (historyIdx <= 0) {
                            historyIdx = -1
                            text = ""
                            return
                        }
                        historyIdx--
                        text = history[history.length - 1 - historyIdx]
                    }
                }

                Button {
                    text: "Run"
                    enabled: adbShellBridge.connected && cmdField.text.trim() !== ""
                    Material.accent: Material.Teal
                    onClicked: root.sendCmd()
                }

                Button {
                    text: "Clear"
                    flat: true
                    onClicked: outputArea.text = ""
                }
            }
        }
    }

    // ── Bridge signal handlers ────────────────────────────────────────────

    Connections {
        target: adbShellBridge

        function onLineReceived(line) {
            // Trim buffer to maxLines to avoid unbounded memory growth
            var lines = outputArea.text.split("\n")
            if (lines.length > root.maxLines) {
                lines = lines.slice(lines.length - root.maxLines)
                outputArea.text = lines.join("\n")
            }
            outputArea.text += line + "\n"
        }

        function onSessionEnded(code) {
            var suffix = (code !== 0) ? " (exit " + code + ")" : ""
            outputArea.text += "\n[Session ended" + suffix
                + " — press Connect to reconnect]\n"
        }

        function onErrorOccurred(msg) {
            outputArea.text += "\n[Error: " + msg + "]\n"
        }

        function onConnectedChanged() {
            if (adbShellBridge.connected) {
                outputArea.text += "[Connected]\n"
                cmdField.forceActiveFocus()
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    function sendCmd() {
        var cmd = cmdField.text.trim()
        if (cmd === "") return

        outputArea.text += "$ " + cmd + "\n"

        // Save to history (avoid consecutive duplicates)
        if (cmdField.history.length === 0 ||
                cmdField.history[cmdField.history.length - 1] !== cmd) {
            cmdField.history.push(cmd)
        }
        cmdField.historyIdx = -1
        cmdField.text = ""

        if (adbShellBridge.connected) {
            adbShellBridge.sendLine(cmd)
        } else {
            // One-shot fallback when persistent session is not open
            var out = adbShellBridge.runCommand(cmd)
            outputArea.text += out + "\n"
        }
    }

    // Auto-connect when the page is created (if in native mode)
    Component.onCompleted: {
        if (root.useNative) {
            adbShellBridge.connectShell()
        }
    }

    Component.onDestruction: {
        if (root.useNative) {
            adbShellBridge.disconnectShell()
        }
    }
}
