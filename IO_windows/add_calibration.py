from PyQt6 import QtWidgets, uic
import os
import sys

class add_calibration(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super(add_calibration, self).__init__()

        #Load the UI Page
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'add_calibration.ui'), self)

        # Connect the button clicked signal
        self.buttonBox.clicked.connect(self.process_click)

        # Define the calibration file path
        self.cali_path = os.path.join(os.path.dirname(__file__), '..', 'Inversion_functions', 'calibration_list.txt')

    def accept(self):
        # Redefine accept so that the response is not automatically accepted when an invalid equation is used
        pass

    def process_click(self, button):
        # Only do something if save has been pressed
        if button.text() != 'Save':
            return

        # Get the fitting equation
        fitting_equation = self.fittingEquation.toPlainText().lower()

        try:
            # Test the fitting equation
            r = 2
            eval(fitting_equation)

        except (SyntaxError, NameError):
            # Raise an error if the fitting equation is invalid
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Invalid expression")
            dlg.setText("The equation provided is not a function of r only. Please try again.\n\nEquation syntax:\n\tr*2:  multiply r by 2\n\tr**2:  raise r to the power 2.")
            dlg.exec()

            # Do not accept the input
            return

        # Write out to the calibration file
        with open(self.cali_path, 'a') as f:
            f.write(f'{self.caliName.text()}\t{self.maxRadius.value()}\t{self.interpolateRadius.isChecked()}\t{fitting_equation}\n')

        # Accept the input
        super(add_calibration, self).accept()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    testWindow = add_calibration()
    testWindow.show()
    app.exec()