from PyQt6 import QtWidgets, uic
import sys
import os

class loadParameters(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super(loadParameters, self).__init__()

        #Load the UI Page
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'load_parameters.ui'), self)

        # Set up load parameter button
        self.loadParameterFileButton.clicked.connect(self.load_parameter_file)

        # Initialise the default save folder
        self.cur_path = ''

        # Make the table read-only
        delegate = StyledItemDelegate(self.parameterTable)
        self.parameterTable.setItemDelegate(delegate)


    def load_parameter_file(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, f'Load parameter file', self.cur_path, "Parameters file(parameters.txt);;Txt files (*.txt);;All files (*.*)")[0]

        if fname == '':
            return

        # Set parameter file display
        self.parameterFilePath.setText(fname)

        # Clear the previous table
        no_rows = self.parameterTable.rowCount()
        for i in range(no_rows):
            self.parameterTable.removeRow(0)

        with open(fname, 'r') as f:
            for line in f:
                # Process each line of the file
                line = line.strip().split('\t')
                if line == ['']: continue

                # Get the current row count (will become the new index)
                i = self.parameterTable.rowCount()

                # Add a new row
                self.parameterTable.insertRow(i)

                # Populate table from the calibration file
                for j in range(9):
                    self.parameterTable.setItem(i, j, QtWidgets.QTableWidgetItem(line[j]))

    def set_default_path(self, cur_path):
        self.cur_path = cur_path

    def set_parameters(self, main_var):
        # Get the current row
        parameter_row = self.parameterTable.currentRow()

        # Do not do anything if nothing in the table is selected
        if parameter_row == -1: return

        # Set the parameters #########################
        # Image centre
        img_centre = eval(self.parameterTable.item(parameter_row, 1).text())
        main_var.xCentrePos.setValue(img_centre[0])
        main_var.yCentrePos.setValue(img_centre[1])

        # Image limits
        main_var.ToF_limit_one.setValue(int(self.parameterTable.item(parameter_row, 2).text()))
        main_var.ToF_limit_two.setValue(int(self.parameterTable.item(parameter_row, 3).text()))

        # Detector mask parameters
        detector_mask_parameters = eval(self.parameterTable.item(parameter_row, 4).text())
        # These are all the options for the various possible states
        if detector_mask_parameters[0] and main_var.imageInversion.detectorMask.detector_mask:
            main_var.imageInversion.detectorMask.circle_ROI.setPos(detector_mask_parameters[1])
            main_var.imageInversion.detectorMask.circle_ROI.setSize(detector_mask_parameters[2])

        else:
            if main_var.imageInversion.detectorMask.detector_mask:
                main_var.imageInversion.detectorMask.toggle(main_var.main_image.widget)

            main_var.imageInversion.detectorMask.pos = detector_mask_parameters[1]
            main_var.imageInversion.detectorMask.size = detector_mask_parameters[2]

            if detector_mask_parameters[0]:
                main_var.imageInversion.detectorMask.toggle(main_var.main_image.widget)


        # Inversion method
        idx = main_var.inversionMethod.findText(self.parameterTable.item(parameter_row, 5).text())
        main_var.inversionMethod.setCurrentIndex(idx)

        # # Inversion parameters
        inversion_params = eval('{' + self.parameterTable.item(parameter_row, 6).text() + '}')
        main_var.basisFunctionWidthBASEX.setValue(inversion_params['sigmaBASEX'])
        main_var.regStrengthBASEX.setValue(inversion_params['regStrengthBASEX'])
        main_var.regStrengthRBASEX.setValue(inversion_params['regStrengthRBASEX'])
        main_var.regStrengthPBASEX.setValue(inversion_params['regStrengthPBASEX'])
        main_var.regMethodComboRBASEX.setCurrentIndex(main_var.regMethodComboRBASEX.findText(inversion_params['regMethodRBASEX']))
        main_var.maxBeta.setValue(inversion_params['beta_order'])
        main_var.useOddBeta.setChecked(inversion_params['odd_beta'])
        main_var.pBASEXBasisSet.setText(inversion_params['pBASEXBasisSet'])

        # Mass and charge
        mass, charge = eval(self.parameterTable.item(parameter_row, 7).text())
        main_var.ionMassCombo.setValue(mass); main_var.ionChargeCombo.setValue(charge)

        # # Calibration parameters
        cali_parameters = self.parameterTable.item(parameter_row, 8).text()
        if cali_parameters == 'No cali':
            try:
                # Clear the calibration data
                del main_var.imageInversion.radial_dist_converter.cali_data
                # Reset the ability to save calibrated data
                main_var.save_window.disable_cali_saves()
                # Set variables to the state for the case where no calibration is loaded
                main_var.currentCalibration.setText('None loaded')
                main_var.save_window.calibration_loaded = False
                main_var.distTypeCombo.setEnabled(False)
                main_var.distTypeCombo.setCurrentIndex(0)
            except AttributeError:
                pass # No calibration loaded yet :)
        else:
            # Read the calibration data
            cali_data_raw = [element.split(': ') for element in self.parameterTable.item(parameter_row, 8).text().split(', ')]
            # Convert non-str values to the appropriate values
            cali_data_raw[1][1] = float(cali_data_raw[1][1]); cali_data_raw[2][1] = eval(cali_data_raw[2][1])
            # Populate the calibration data dict
            cali_data = {element[0]: element[1] for element in cali_data_raw}
            # Set the calibration data
            main_var.load_energy_calibration_file(load_from_parameter_file=True, cali_data=cali_data)



class StyledItemDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, *args):
        editor = super().createEditor(*args)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setReadOnly(True)
        return editor


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    testWindow = loadParameters()
    testWindow.show()
    app.exec()