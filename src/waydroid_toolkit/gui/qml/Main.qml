// Main.qml — WayDroid Toolkit application shell
// Material style, navigation drawer + StackView page routing
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root
    // Aliases used by child pages loaded into the StackView.
    // applicationWindow.showToast(msg, isError) — global toast
    // applicationWindow.pageStack.replace(url) — navigate to a page
    property alias applicationWindow: root
    readonly property alias pageStack: pageStack

    title: "WayDroid Toolkit"
    width: 960
    height: 680
    minimumWidth: 720
    minimumHeight: 520
    visible: true

    Material.theme: Material.System
    Material.accent: Material.Teal
    Material.primary: Material.Teal

    // ── Navigation model ──────────────────────────────────────────────────
    readonly property var navItems: [
        { id: "status",      label: "Status",      icon: "qrc:/icons/status.svg",      page: "pages/StatusPage.qml"      },
        { id: "backend",     label: "Backend",     icon: "qrc:/icons/backend.svg",     page: "pages/BackendPage.qml"     },
        { id: "extensions",  label: "Extensions",  icon: "qrc:/icons/extensions.svg",  page: "pages/ExtensionsPage.qml"  },
        { id: "packages",    label: "Packages",    icon: "qrc:/icons/packages.svg",    page: "pages/PackagesPage.qml"    },
        { id: "images",      label: "Images",      icon: "qrc:/icons/images.svg",      page: "pages/ImagesPage.qml"      },
        { id: "performance", label: "Performance", icon: "qrc:/icons/performance.svg", page: "pages/PerformancePage.qml" },
        { id: "backup",      label: "Backup",      icon: "qrc:/icons/backup.svg",      page: "pages/BackupPage.qml"      },
        { id: "maintenance", label: "Maintenance", icon: "qrc:/icons/maintenance.svg", page: "pages/MaintenancePage.qml" },
        { id: "logcat",      label: "Logcat",      icon: "qrc:/icons/logcat.svg",      page: "pages/LogcatPage.qml"      },
        { id: "terminal",    label: "Terminal",    icon: "qrc:/icons/terminal.svg",    page: "pages/TerminalPage.qml"    },
    ]

    property int currentNavIndex: 0

    // ── Global toast ──────────────────────────────────────────────────────
    WdtToast { id: toast; parent: Overlay.overlay }

    function showToast(msg, isError) { toast.show(msg, isError) }

    // ── Error forwarding from all bridges ─────────────────────────────────
    Connections { target: statusBridge;      function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: backendBridge;     function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: extensionsBridge;  function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: packagesBridge;    function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: performanceBridge; function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: backupBridge;      function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: imagesBridge;      function onErrorOccurred(m) { showToast(m, true) } }
    Connections { target: maintenanceBridge; function onErrorOccurred(m) { showToast(m, true) } }

    // ── Layout ────────────────────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Navigation rail (permanent on wide screens)
        Pane {
            id: navRail
            Layout.fillHeight: true
            width: 200
            padding: 0
            Material.elevation: 2

            background: Rectangle {
                color: Material.color(Material.Teal, Material.Shade800)
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // App header
                Item {
                    Layout.fillWidth: true
                    height: 64

                    Label {
                        anchors.centerIn: parent
                        text: "WayDroid"
                        font.pixelSize: 18
                        font.weight: Font.Medium
                        color: "white"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Qt.rgba(1, 1, 1, 0.15)
                }

                // Nav items
                ListView {
                    id: navList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: root.navItems
                    currentIndex: root.currentNavIndex
                    clip: true

                    delegate: ItemDelegate {
                        width: navList.width
                        height: 48
                        highlighted: ListView.isCurrentItem

                        background: Rectangle {
                            color: parent.highlighted
                                   ? Qt.rgba(1, 1, 1, 0.15)
                                   : (parent.hovered ? Qt.rgba(1, 1, 1, 0.08) : "transparent")
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }

                        contentItem: RowLayout {
                            spacing: 12
                            leftPadding: 16

                            Label {
                                text: modelData.label
                                color: "white"
                                font.pixelSize: 14
                                font.weight: parent.parent.highlighted ? Font.Medium : Font.Normal
                            }
                        }

                        onClicked: {
                            root.currentNavIndex = index
                            pageStack.replace(Qt.resolvedUrl(modelData.page))
                        }
                    }
                }

                // Version footer
                Label {
                    Layout.fillWidth: true
                    text: appVersion
                    color: Qt.rgba(1, 1, 1, 0.5)
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    bottomPadding: 8
                    topPadding: 8
                }
            }
        }

        // Page area
        StackView {
            id: pageStack
            Layout.fillWidth: true
            Layout.fillHeight: true

            initialItem: Qt.resolvedUrl("pages/StatusPage.qml")

            replaceEnter: Transition {
                PropertyAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
            }
            replaceExit: Transition {
                PropertyAnimation { property: "opacity"; from: 1; to: 0; duration: 100 }
            }
        }
    }

    // Load status on startup
    Component.onCompleted: statusBridge.refresh()
}
