from PyQt6 import QtWidgets, uic
import os
import sys
from shutil import copyfile
try:
    from IO_windows.add_calibration import add_calibration
except ModuleNotFoundError:
    from add_calibration import add_calibration


class load_calibration(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super(load_calibration, self).__init__()

        #Load the UI Page
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'load_calibration.ui'), self)

        # Make the table read-only
        delegate = StyledItemDelegate(self.calibrationTable)
        self.calibrationTable.setItemDelegate(delegate)

        self.cali_path = os.path.join(os.path.dirname(__file__), '..', 'Inversion_functions', 'calibration_list.txt')
        # Check the calibration list has been initialised
        if not os.path.exists(self.cali_path):
            copyfile(os.path.join(os.path.dirname(__file__), '..', 'Inversion_functions', 'calibration_list_template.txt'), self.cali_path)

        # Populate the calibration table
        self.populate_table()

        # Initialise the connections
        self.loadCalibration.clicked.connect(self.get_cali)
        self.addCalibration.clicked.connect(self.add_cali)


    def populate_table(self):
        with open(self.cali_path, 'r') as f:
            # Skip header
            f.readline(); f.readline()

            # Define index term
            idx = 0

            for line in f:
                # Skip poppulated rows when updating the table after adding a new calibration
                if self.calibrationTable.rowCount() > idx:
                    idx += 1
                    continue

                # Process each line of the file
                line = line.strip().split('\t')
                if line == ['']: continue

                # Add a new row
                self.calibrationTable.insertRow(idx)

                # Populate table from the calibration file
                for j in range(4):
                    self.calibrationTable.setItem(idx, j, QtWidgets.QTableWidgetItem(line[j]))

                idx += 1


    def get_cali(self):
        # Get the current row
        cali_row = self.calibrationTable.currentRow()

        if cali_row == -1: return

        # Read the information in the items
        self.cali_data = {
            'name': self.calibrationTable.item(cali_row, 0).text(),
            'max_r': float(self.calibrationTable.item(cali_row, 1).text()),
            'interpolate': eval(self.calibrationTable.item(cali_row, 2).text()),
            'equation': self.calibrationTable.item(cali_row, 3).text()
        }

        # Accept the new calibration
        self.accept()

    def add_cali(self):
        # Open the add calibration dialogue
        caliDialogue = add_calibration()
        new_cali_added = caliDialogue.exec()

        if new_cali_added:
            # Repopulate the table if a valid new calibration added
            self.populate_table()

            # Select the new calibration
            self.calibrationTable.selectRow(self.calibrationTable.rowCount() - 1)


class StyledItemDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, *args):
        editor = super().createEditor(*args)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setReadOnly(True)
        return editor

if __name__=='__main__':
    app = QtWidgets.QApplication(sys.argv)
    testWindow = load_calibration()
    testWindow.show()
    app.exec()

    print(testWindow.cali_data)