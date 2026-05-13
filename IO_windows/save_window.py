from PyQt6 import QtWidgets, uic
import PyQt6.QtGui as QtGui
import sys
import os
import numpy as np
import time

class SaveWindow(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super(SaveWindow, self).__init__()

        #Load the UI Page
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'save_window.ui'), self)

        # Set default identifiers for saved files
        identifier_file = file_path = os.path.join(os.path.dirname(__file__), 'identifier_extensions.txt')
        if not os.path.exists(identifier_file):
            generate_default_identifiers(identifier_file)
        # Loop through all lines and set the text as required
        with open(identifier_file, 'r') as f:
            for line in f:
                line = line.strip().split('\t')
                try:
                    exec(f"self.{line[0]}.setText('{line[1]}')")
                except AttributeError as e:
                    print(f'Attribute Error: Unexpected parameter in the identifier file: {str(e).split()[-1]}')

        # Set up folder select button
        self.getOutputFolder.clicked.connect(self.set_default_path)

        # Initialise the default save folder
        self.cur_path = ''

        self.calibration_loaded = False


    def set_default_path(self, *args, default_path=None):
        if default_path == None:
            default_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select folder', self.cur_path)

        # Set the paths
        if default_path != '':
            self.cur_path = default_path
        self.outputFolder.setText(self.cur_path)

    # Functions to enable the saving of parameters as the corresponding fields are plotted
    def enable_ToF(self):
        self.saveToF.setEnabled(True)

    def enable_mz_ToF(self):
        self.saveMzToF.setEnabled(True)

    def enable_ion_im(self):
        self.saveIonImage.setEnabled(True)
        self.saveIonImage.setChecked(True)

    def enable_inv_im(self):
        self.saveSymmetrisedImage.setEnabled(True)
        self.saveInvertedImage.setEnabled(True)
        self.saveRadialDist.setEnabled(True)
        self.saveBetaDist.setEnabled(True)

        self.saveSymmetrisedImage.setChecked(True)
        self.saveInvertedImage.setChecked(True)
        self.saveRadialDist.setChecked(True)
        self.saveBetaDist.setChecked(True)

        if self.calibration_loaded:
            self.enable_cali_saves()

    def enable_cali_saves(self):
        self.saveVelocityDist.setEnabled(True)
        self.saveMomentumDist.setEnabled(True)
        self.saveEnergyDist.setEnabled(True)

        self.saveEnergyDist.setChecked(True)

    def disable_cali_saves(self):
        self.saveVelocityDist.setEnabled(False)
        self.saveMomentumDist.setEnabled(False)
        self.saveEnergyDist.setEnabled(False)
        

    def toggle_save_buttons(self):
        self.saveAll.setEnabled(not self.saveAll.isEnabled())
        self.saveSelected.setEnabled(not self.saveSelected.isEnabled())

    def save_selected(self, main_var, save_all=False):
        # Begin to contruct file names
        save_folder = self.outputFolder.text()
        base_filename = self.baseFileName.text()

        # Save the parameters from the main window if requested
        if self.checkSaveParameters.isChecked():
            self.save_parameters(main_var, save_folder, base_filename)

        # Add an underscore to separate the base filename from the differentiating extension
        if base_filename != '': base_filename += '_'

        # Iterate through the different parameters that can be saved
        # ToF
        if self.saveToF.isChecked() or (self.saveToF.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionToF.text()}.dat')
            np.savetxt(fname, 
                        np.vstack((main_var.main_ToF.x_values, main_var.main_ToF.tof)).T,
                        delimiter='\t')

        # m/z ToF
        if self.saveMzToF.isChecked() or (self.saveMzToF.isEnabled() and save_all):
            try:
                # Get the intensity (applying appropriate Jacobian)
                intensity = main_var.main_ToF.tof[main_var.mass_cali_tab.min_time:] / main_var.mass_cali_tab.m_q ** 0.5
                
                fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionMz.text()}.dat')
                np.savetxt(fname, 
                            np.vstack((main_var.mass_cali_tab.m_q, intensity / max(intensity) * 100)).T,
                            delimiter='\t')

            except AttributeError:
                pass

        # Ion image
        if self.saveIonImage.isChecked() or (self.saveIonImage.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionIonIm.text()}.dat')
            np.savetxt(fname, 
                        main_var.main_image.ionImage,
                        delimiter='\t')

        # Symmetrised image
        if self.saveSymmetrisedImage.isChecked() or (self.saveSymmetrisedImage.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionSymIm.text()}.dat')
            np.savetxt(fname, 
                        main_var.imageInversion.inversion_class.symmetrised_image[0],
                        delimiter='\t')

        # Inverted image
        if self.saveInvertedImage.isChecked() or (self.saveInvertedImage.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionInvIm.text()}.dat')
            np.savetxt(fname, 
                        main_var.imageInversion.inversion_class.inverted_image[0],
                        delimiter='\t')

        # Radial distribution
        if self.saveRadialDist.isChecked() or (self.saveRadialDist.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionRadDist.text()}.dat')
            np.savetxt(fname, 
                        np.vstack((main_var.imageInversion.inversion_class.radius, main_var.imageInversion.inversion_class.radial_intensity[0])).T,
                        delimiter='\t')

        # Velocity distribution
        if self.saveVelocityDist.isChecked() or (self.saveVelocityDist.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionVelDist.text()}.dat')
            # Get the veolcity-calibrated distribution (normalised)
            x_coords, y_coords = main_var.imageInversion.radial_dist_converter.fun_velocity(
                        main_var.imageInversion.inversion_class.radius, 
                        main_var.imageInversion.inversion_class.radial_intensity[0],
                        True, 0
            )
            # Save the distribution
            np.savetxt(fname, 
                        np.vstack((x_coords, y_coords)).T,
                        delimiter='\t')

        # Momentum distribution
        if self.saveMomentumDist.isChecked() or (self.saveMomentumDist.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionMomDist.text()}.dat')
            # Get the momentum-calibrated distribution (normalised)
            x_coords, y_coords = main_var.imageInversion.radial_dist_converter.fun_momentum(
                        main_var.imageInversion.inversion_class.radius, 
                        main_var.imageInversion.inversion_class.radial_intensity[0],
                        True, 0
            )
            # Save the distribution
            np.savetxt(fname, 
                        np.vstack((x_coords, y_coords)).T,
                        delimiter='\t')

        # Energy distribution
        if self.saveEnergyDist.isChecked() or (self.saveEnergyDist.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionEDist.text()}.dat')
            # Get the veolcity-calibrated distribution (normalised)
            x_coords, y_coords = main_var.imageInversion.radial_dist_converter.fun_energy(
                        main_var.imageInversion.inversion_class.radius, 
                        main_var.imageInversion.inversion_class.radial_intensity[0],
                        True, 0
            )
            # Save the distribution
            np.savetxt(fname, 
                        np.vstack((x_coords, y_coords)).T,
                        delimiter='\t')

        # Beta distribution
        if self.saveBetaDist.isChecked() or (self.saveBetaDist.isEnabled() and save_all):
            fname = os.path.join(save_folder, f'{base_filename + self.defaultExtensionBetaDist.text()}.dat')
            np.savetxt(fname, 
                        main_var.imageInversion.inversion_class.beta[0].T,
                        delimiter='\t')


    def save_parameters(self, main_var, save_folder, base_filename):
        # Generate the file name
        fname = os.path.join(save_folder, 'parameters.txt')

        # Get the parameters
        parameter_list = [''] * 9
        parameter_list[0] = base_filename # File being saved
        parameter_list[1] = str((main_var.xCentrePos.value(), main_var.yCentrePos.value())) # Image centre
        parameter_list[2] = str(main_var.ToF_limit_one.value()) # Image limit one
        parameter_list[3] = str(main_var.ToF_limit_two.value()) # Image limit two
        parameter_list[4] = str([main_var.imageInversion.detectorMask.detector_mask,
                                main_var.imageInversion.detectorMask.pos,
                                main_var.imageInversion.detectorMask.size]) # Detector mask (Applied, (pos), (size))
        parameter_list[5] = str(main_var.inversionMethod.currentText()) # Inversion method

        # Inversion parameters
        parameter_list[6] = f"'sigmaBASEX': {main_var.basisFunctionWidthBASEX.value()}, "
        parameter_list[6] += f"'regStrengthBASEX': {main_var.regStrengthBASEX.value()}, "
        parameter_list[6] += f"'regStrengthRBASEX': {main_var.regStrengthRBASEX.value()}, "
        parameter_list[6] += f"'regStrengthPBASEX': {main_var.regStrengthPBASEX.value()}, "
        parameter_list[6] += f"'regMethodRBASEX': '{main_var.regMethodComboRBASEX.currentText()}', "
        parameter_list[6] += f"'beta_order': {main_var.maxBeta.value()}, "
        parameter_list[6] += f"'odd_beta': {main_var.useOddBeta.isChecked()}, "
        parameter_list[6] += f"'pBASEXBasisSet': '{main_var.pBASEXBasisSet.text()}', "

        # Mass and charge
        parameter_list[7] = f'({main_var.ionMassCombo.value()}, {main_var.ionChargeCombo.value()})'

        # Calibration parameters
        try:
            parameter_list[8] = ', '.join([f'{_key}: {_val}' for _key, _val in main_var.imageInversion.radial_dist_converter.cali_data.items()])
        except AttributeError:
            parameter_list[8] = 'No cali'

        # Write to the parameter file
        with open(fname, 'a') as f:
            f.write('\t'.join(parameter_list) + '\n')




def generate_default_identifiers(file_path):
    # Generate file with the default values to be appended to the file to separate the saved variables
    with open(file_path, 'w') as f:
        f.write(f'defaultExtensionToF\tToF_t\n')
        f.write(f'defaultExtensionMz\tToF_mz\n')
        f.write(f'defaultExtensionIonIm\tion_im\n')
        f.write(f'defaultExtensionSymIm\tsym_im\n')
        f.write(f'defaultExtensionInvIm\tinv_im\n')
        f.write(f'defaultExtensionRadDist\trad_dist\n')
        f.write(f'defaultExtensionVelDist\tvel_dist\n')
        f.write(f'defaultExtensionMomDist\tmom_dist\n')
        f.write(f'defaultExtensionEDist\tE_dist\n')
        f.write(f'defaultExtensionBetaDist\tbeta_dist\n')


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = SaveWindow()
    main.show()
    app.exec()

if __name__ == '__main__':
    main()