import QtQuick
import "../../workspace-map.js" as Machine
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "omarchy.workspaces"
  readonly property var hostScreen: root.QsWindow.window ? root.QsWindow.window.screen : null
  readonly property string monitorName: hostScreen ? hostScreen.name : ""
  readonly property int workspaceOffset: Machine.offsets[monitorName] || 0

  function workspaceById(id) {
    var values = Hyprland.workspaces.values
    for (var i = 0; i < values.length; i++) {
      if (values[i].id === id) return values[i]
    }

    return null
  }

  function workspaceIds() {
    return [1, 2, 3, 4, 5]
  }

  function focusWorkspace(slot) {
    if (!root.bar || !root.monitorName) return
    var id = root.workspaceOffset + slot
    var command = "hl.dsp.focus({ workspace = \"" + id + "\" })"
    root.bar.run("hyprctl dispatch " + Util.shellQuote(command))
  }

  readonly property real trailingGap: root.vertical ? 0 : Style.spaceReal(1.5)

  implicitWidth: grid.implicitWidth + trailingGap
  implicitHeight: grid.implicitHeight

  GridLayout {
    id: grid
    anchors.fill: parent
    anchors.rightMargin: root.trailingGap
    columns: root.vertical ? 1 : root.workspaceIds().length
    columnSpacing: root.vertical ? 0 : Style.space(1)
    rowSpacing: root.vertical ? Style.space(2) : 0

    Repeater {
      model: root.workspaceIds()

      WidgetButton {
        id: button
        required property int modelData
        readonly property var workspace: root.workspaceById(root.workspaceOffset + modelData)
        readonly property bool occupied: workspace !== null && workspace.toplevels.values.length > 0
        readonly property bool focused: workspace !== null && workspace.active && workspace.monitor !== null && workspace.monitor.name === root.monitorName
        bar: root.bar
        text: String(modelData)
        fontSize: 19
        foreground: focused ? Color.accent : Color.foreground
        fixedWidth: root.vertical ? root.barSize : 52
        fixedHeight: 52
        tooltipText: root.monitorName + " screen · Workspace " + modelData + (focused ? " · active" : "")
        Rectangle {
          z: -1
          anchors.centerIn: parent
          width: 52; height: 48; radius: 12
          color: button.focused ? Qt.alpha(Color.accent, 0.18) : button.tooltipHovered ? Qt.alpha(Color.accent, 0.12) : Qt.alpha(Color.foreground, 0.045)
          border.width: 1
          border.color: button.focused || button.tooltipHovered ? Color.accent : Qt.alpha(Color.foreground, 0.2)
          Behavior on color { ColorAnimation { duration: 140 } }
        }
        Rectangle {
          width: 4; height: 4; radius: 2
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.bottom: parent.bottom; anchors.bottomMargin: 7
          visible: button.occupied
          color: Color.accent
        }
        onPressed: function(mouseButton) { if (mouseButton === Qt.LeftButton) root.focusWorkspace(modelData) }
      }
    }
  }
}
