// WebEngineTerminal.qml — loaded dynamically only when QtWebEngine is present
import QtQuick
import QtWebEngine

WebEngineView {
    id: webView

    property url url

    settings.javascriptEnabled: true
    settings.localContentCanAccessRemoteUrls: false
    settings.localContentCanAccessFileUrls: true

    // Allow WebUSB — required for wadb
    settings.unknownUrlSchemePolicy: WebEngineSettings.AllowAllUnknownUrlSchemes

    Component.onCompleted: webView.url = url

    onLoadingChanged: function(info) {
        if (info.status === WebEngineLoadingInfo.LoadFailedStatus) {
            console.warn("wadb terminal failed to load:", info.errorString)
        }
    }
}
