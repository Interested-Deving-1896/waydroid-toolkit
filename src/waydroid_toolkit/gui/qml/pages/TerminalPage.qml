// TerminalPage.qml — wadb-powered ADB terminal via WebEngineView
// Falls back to a plain text ADB shell output view when WebEngine is unavailable.
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Page {
    id: root
    title: "Terminal"

    // wadbHtmlUrl is set by the Python app.py to the local wadb HTML page URL
    property string wadbHtmlUrl: typeof _wadbUrl !== "undefined" ? _wadbUrl : ""
    property bool webEngineAvailable: typeof WebEngineView !== "undefined"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Toolbar ───────────────────────────────────────────────────────
        Pane {
            Layout.fillWidth: true
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
                    text: webEngineAvailable ? "wadb (WebUSB)" : "native adb"
                    font.pixelSize: 12
                    color: Material.hintTextColor
                }

                Button {
                    text: "Reconnect"
                    flat: true
                    Material.accent: Material.Teal
                    onClicked: webEngineAvailable ? webView.reload() : nativeShell.refresh()
                }
            }
        }

        // ── WebEngine terminal (wadb) ─────────────────────────────────────
        Loader {
            id: webEngineLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            active: root.webEngineAvailable && root.wadbHtmlUrl !== ""

            sourceComponent: Component {
                // WebEngineView is conditionally imported — use Loader to avoid
                // import errors when QtWebEngine is not installed
                Item {
                    anchors.fill: parent

                    // Dynamically create WebEngineView to avoid hard import
                    Component.onCompleted: {
                        var comp = Qt.createComponent("WebEngineTerminal.qml")
                        if (comp.status === Component.Ready) {
                            comp.createObject(this, { anchors: { fill: this }, url: root.wadbHtmlUrl })
                        }
                    }
                }
            }
        }

        // ── Fallback: native adb shell output ─────────────────────────────
        ColumnLayout {
            id: nativeShell
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
            padding: 16
            visible: !root.webEngineAvailable || root.wadbHtmlUrl === ""

            function refresh() {
                maintenanceBridge.startLogcat()
            }

            Label {
                text: "WebEngine not available — showing logcat output.\nInstall PySide6-WebEngine for the full wadb terminal."
                wrapMode: Text.WordWrap
                color: Material.hintTextColor
                font.pixelSize: 12
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#1e1e1e"
                radius: 6

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true

                    TextArea {
                        id: logOutput
                        readOnly: true
                        font.family: "monospace"
                        font.pixelSize: 12
                        color: "#d4d4d4"
                        background: null
                        wrapMode: Text.NoWrap

                        Connections {
                            target: maintenanceBridge
                            function onLogcatOutput(output) { logOutput.text = output }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                TextField {
                    id: cmdField
                    Layout.fillWidth: true
                    placeholderText: "adb shell command…"
                    font.family: "monospace"
                    onAccepted: runBtn.clicked()
                }

                Button {
                    id: runBtn
                    text: "Run"
                    Material.accent: Material.Teal
                    onClicked: {
                        if (cmdField.text !== "") {
                            maintenanceBridge.startLogcat()
                            cmdField.clear()
                        }
                    }
                }
            }
        }
    }
}
