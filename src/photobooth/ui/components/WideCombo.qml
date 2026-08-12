import QtQuick.Controls.Basic
import QtQuick.Layouts

// Uniform-width field control: every selector/combobox/textbox on the
// Settings screen uses one of these (WideCombo/WideText/WideSpin) so they
// all line up at the same width, while still shrinking responsively
// (fillWidth) below that cap on narrow screens.
ComboBox {
    Layout.fillWidth: true
    Layout.preferredWidth: 420
    Layout.maximumWidth: 420
}
