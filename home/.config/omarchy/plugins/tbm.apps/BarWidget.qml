import Quickshell
import QtQuick
import qs.Commons
import qs.Ui
BarWidget {
  id: root
  implicitWidth: root.barSize
  implicitHeight: root.barSize
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "apps"
    fontSize: 12
    tooltipText: "Apps"
    onPressed: function(mouseButton) {
      if (mouseButton !== Qt.LeftButton || !root.bar) return
      var window = root.QsWindow.window
      var point = root.mapToItem(null, 0, 0)
      var payload = JSON.stringify({menu:"apps", screen:window.screen.name, x:window.width + 8, y:point.y})
      root.bar.run("omarchy-shell shell toggle tbm.apps " + Util.shellQuote(payload))
    }
  }
}
