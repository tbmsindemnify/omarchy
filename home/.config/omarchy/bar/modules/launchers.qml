import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import qs.Commons
import qs.Ui
BarWidget {
  id: root
  implicitWidth: root.vertical ? root.barSize : grid.implicitWidth
  implicitHeight: grid.implicitHeight + 22
  GridLayout {
    id: grid
    anchors.centerIn: parent
    columns: root.vertical ? 1 : 5
    rowSpacing: 8; columnSpacing: 8
    Repeater {
      model: [
        { icon: "windows", name: "Windows virtual machine", command: "@@HOME@@/.config/omarchy/bar/launch-windows" },
        { icon: "openai", name: "Codex", command: "@@HOME@@/.config/omarchy/bar/launch-codex" },
        { icon: "hermes", name: "Hermes Agent", command: "@@HOME@@/.local/bin/hermes-desktop-app" },
        { icon: "claude", name: "Claude", command: "@@HOME@@/.config/omarchy/bar/launch-claude" },
        { icon: "edge", name: "Microsoft Edge", command: "@@HOME@@/.config/omarchy/bar/launch-edge" }
      ]
      WidgetButton {
        id: button
        required property var modelData
        bar: root.bar
        text: modelData.name
        labelVisible: false
        fixedWidth: 52; fixedHeight: 52
        tooltipText: modelData.name
        Rectangle {
          z: -1
          anchors.fill: parent
          radius: 13
          color: button.tooltipHovered ? Qt.alpha(Color.accent, 0.17) : Qt.alpha(Color.foreground, 0.045)
          border.width: 1
          border.color: button.tooltipHovered ? Color.accent : Qt.alpha(Color.foreground, 0.2)
          Behavior on color { ColorAnimation { duration: 150 } }
        }
        Image {
          anchors.centerIn: parent
          width: button.modelData.icon === "hermes" ? 40 : 30
          height: button.modelData.icon === "hermes" ? 40 : 30
          source: button.modelData.icon === "hermes"
            ? "icons/hermes.svg"
            : "icons/" + button.modelData.icon + ".svg"
          sourceSize.width: 80; sourceSize.height: 80
          fillMode: Image.PreserveAspectFit
          smooth: true
          layer.enabled: true
          layer.effect: MultiEffect {
            colorization: 1.0
            colorizationColor: button.tooltipHovered ? Color.accent : Color.bar.text
          }
        }
        onPressed: function(mouseButton) {
          if (mouseButton === Qt.LeftButton && root.bar) root.bar.run(modelData.command)
        }
      }
    }
  }
}
