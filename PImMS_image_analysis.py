from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pyqtgraph import PlotWidget, plot
from Plotters import ToF_plotter, image_plotter, inversion_plotter
from Centroiding import centroid_widgets
from Calibration.mass_calibration import mass_calibration
import pyqtgraph as pg
import sys
import os
import numpy as np
from IO_windows.save_window import SaveWindow as SaveWindow
from IO_windows.load_calibration import load_calibration
from IO_windows.load_parameters import loadParameters

pg.setConfigOption('foreground', 'k')
pg.setConfigOption('background', 'w')


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'analysis_layout.ui'), self)

        # Set the default path for file dialogues
        self.cur_path = os.path.expanduser(r'~\Documents')

        # Open file dialogue when button pressed
        self.openFile.clicked.connect(lambda: self.select_file(self.fileName))
        self.bgOpenFile.clicked.connect(lambda: self.select_file(self.bgFileName))

        # Initialise the loading GIF
        self.initialise_loading_gif()

        # Open file dialogue when button pressed
        self.openCentroidFolder.clicked.connect(self.select_folder)

        # Define whether item has been plotted to allow top menu to save
        # Initialises at one
        self.items_plotted = {'ToF': 0, 'ionImage': 0, 'invertedImage': 0, 'clusterSizeArray': 0}

        # Set up the tabs
        self.plot_ToF_range_tab()
        self.centroid_tab()
        self.invert_image_tab()
        self.mass_cali_tab()
        self.background_tab()

        # Initialise the load parameters window
        self.load_parameters = loadParameters()
        self.actionLoad_parameters.triggered.connect(self.open_load_parameters_window)
        self.load_parameters.setParametersButton.clicked.connect(lambda: self.load_parameters.set_parameters(self))

        # Initial set-up off top menu
        self.setup_top_menu()

        # Initialise the execution queue
        self.execution_queue = []

        # Generate the function dictionary
        self.function_dict = dict()
        self.function_dict['plot_ToF'] = (self.main_ToF.get_tof, 'ToF')
        self.function_dict['plot_image'] = (self.main_image.getIonImage, 'ionImage')
        self.function_dict['invert_image'] = (self.imageInversion.invert_image, 'invertedImage')
        self.function_dict['centroid_file'] = (self.main_centroid.run_single_file, 'clusterSizeArray')
        self.function_dict['centroid_folder'] = (self.main_centroid.run_all_folders, 'clusterSizeArray')

        self.function_running = False

        # Pointer to the last file type opened
        self.last_file_type = 0

        # Initialise the save window
        self.save_window = SaveWindow()
        self.save_window.saveAll.clicked.connect(lambda: self.save_window.save_selected(self, save_all=True))
        self.save_window.saveSelected.clicked.connect(lambda: self.save_window.save_selected(self, save_all=False))

        # Initialise the load calibration button
        self.loadCalibration.clicked.connect(self.load_energy_calibration_file)


    def initialise_loading_gif(self):
        # Loading the GIF
        self.loadGIF = QMovie(os.path.join(os.path.dirname(__file__), 'Assets', 'loading.gif'))
        self.loadingWidget.setMovie(self.loadGIF)
        self.loadGIF.start()
        self.loadingWidget.hide()

    ############################################
    # Queuing functions
    ############################################
    def append_execution_queue(self, button_pressed, *args):
        data = (button_pressed, *args)

        # No need to run a duplicate
        if data in self.execution_queue:
            return

        # Add event to the queue
        self.execution_queue.append(data)

        # Run the next item if there is not another function running
        if self.function_running == False:
            self.run_next_queue()

    def run_next_queue(self):
        # Get the function and arguments from the queue
        # pop not used so errant double-clicks are not processed twice!
        _function, *args = self.execution_queue[0]

        # Run the function and return the thread so that a finished
        # signal can be added
        worker_thread = self.function_dict[_function][0](*args)

        # Set the function running flag to true
        self.function_running = True

        # Increment the items plotted (only needs to be initialised at one)
        self.items_plotted[self.function_dict[_function][1]] += 1

        # Handle the queue after the calculation is complete.
        # The try statement is used to handle cases where a QThread is not created
        # in the first place, for example in centroiding.py
        try:
            # Check the queue after the calculation is complete
            worker_thread.finished.connect(self.calculation_ended)

        except AttributeError as e:
            if worker_thread == 0:
                self.calculation_ended()
            else:
                print('ARGH')
                raise Exception('An unexpected event occurred. See above for the error.')

    def calculation_ended(self):
        # Set the function running flag to false
        self.function_running = False

        # Update the mirrored ToFs
        if self.execution_queue[0][0] == 'plot_ToF':
            try:
                self.mass_cali_tab.update_tof(self.main_ToF.tof)
            except AttributeError:
                pass

        # Remove the item which has just run from the queue
        self.execution_queue.pop(0)

        # Update the top menu to enable anything new
        self.setup_top_menu()

        # Run a queued function if one exists
        if len(self.execution_queue) > 0:
            self.run_next_queue()

    ############################################
    # Top menu
    ############################################
    def setup_top_menu(self):
        # Need to initialise the save buttons only once. Add one after initialisation to prevent repeats.
        if self.items_plotted['ToF'] == 1:
            self.items_plotted['ToF'] += 1
            self.save_window.enable_ToF(); self.save_window.enable_mz_ToF()
            self.actionSave_ToF.triggered.connect(
                    lambda: self.save_output_file(np.vstack((self.main_ToF.x_values, self.main_ToF.tof)).T, 'ToF'))

            self.actionSave_ToF_m_z.triggered.connect(self.save_mass_calibrated_tof)

        if self.items_plotted['ionImage'] == 1:
            self.items_plotted['ionImage'] += 1
            self.save_window.enable_ion_im()
            self.actionSave_ion_image.triggered.connect(
                    lambda: self.save_output_file(self.main_image.ionImage, 'ion_image'))

        if self.items_plotted['invertedImage'] == 1:
            self.items_plotted['invertedImage'] += 1
            self.save_window.enable_inv_im()
            self.actionSave_symmetrised_image.triggered.connect(
                    lambda: self.save_output_file(self.imageInversion.inversion_class.symmetrised_image[0], 'symmetrised image'))
            
            self.actionSave_inverted_image.triggered.connect(
                    lambda: self.save_output_file(self.imageInversion.inversion_class.inverted_image[0], 'inverted image'))

            self.actionRadial_distribution.triggered.connect(
                lambda: self.save_output_file(
                    np.vstack((self.imageInversion.inversion_class.radius, self.imageInversion.inversion_class.radial_intensity[0])).T,
                    'radial distribution'
                    )
            )

            self.actionBeta_distribution.triggered.connect(
                lambda: self.save_output_file(
                    self.imageInversion.inversion_class.beta[0].T,
                    'beta distribution'
                    )
            )

        if self.items_plotted['clusterSizeArray'] == 1:
            self.items_plotted['clusterSizeArray'] += 1
            self.actionSave_cluster_size_distribution.triggered.connect(
                    lambda: self.save_output_file(np.vstack((np.arange(1,501), self.main_centroid.clustersize_array)).T, 'cluster size distribution'))

        self.actionSave_all.triggered.connect(self.open_save_window)

    def save_mass_calibrated_tof(self):
        try:
            # Plot the data (applying appropriate Jacobian)
            intensity = self.main_ToF.tof[self.mass_cali_tab.min_time:] / self.mass_cali_tab.m_q ** 0.5
            self.save_output_file(np.vstack((self.mass_cali_tab.m_q, intensity / max(intensity) * 100)).T, 'ToF')

        except AttributeError as e:
            pass


    ############################################
    # Tabs
    ############################################
    def plot_ToF_range_tab(self):
        # Set up ToF widget
        self.main_ToF = ToF_plotter(self, self.ToF_limit_one, self.ToF_limit_two)

        # Set up ion image widget
        self.main_image = image_plotter(self)

        # Plot ToF pressed
        self.plotToF.clicked.connect(lambda: self.append_execution_queue('plot_ToF', self.fileName.text(), self.bgFileName.text(), self.loadingWidget))
        self.plotToF_3.clicked.connect(lambda: self.append_execution_queue('plot_ToF', self.fileName.text(), self.bgFileName.text(), self.loadingWidget))

        # Plot image pressed
        self.plotImage.clicked.connect(lambda: self.append_execution_queue('plot_image', self.fileName.text(), self.bgFileName.text(), self.ToF_limit_one.value(), self.ToF_limit_two.value()))

        # Change image contrast
        self.ionImageContrast.valueChanged.connect(lambda: self.main_image.change_contrast(self.ionImageContrast.value()))

        # Transpose
        self.transpose.stateChanged.connect(self.main_image.process_image_transpose)

    def mass_cali_tab(self):
        self.mass_cali_tab = mass_calibration(self)

        # Add pointers to the mass calibration displays
        self.main_ToF.tofLimOneMz = self.tofLimOneMz
        self.main_ToF.tofLimTwoMz = self.tofLimTwoMz

        # Add an array of functions to call after the mass calibration is complete to the mass calibtration class
        self.mass_cali_tab.post_cali_functions = [self.main_ToF.set_mass_calibration]

    def centroid_tab(self):
        # Set up the tab
        self.main_centroid = centroid_widgets(self)

        # Make the centroid buttons work
        self.centroidButton.clicked.connect(lambda: self.append_execution_queue('centroid_file', self))
        self.centroidFolderButton.clicked.connect(lambda: self.append_execution_queue('centroid_folder', self))

    def invert_image_tab(self):
        # Set up the inversion plotter class
        self.imageInversion = inversion_plotter(self)

        # Connect the detector mask button
        self.detectorMaskButton.clicked.connect(lambda: self.imageInversion.toggle_detector_mask(self.main_image.widget))

        # Connect the invert button
        self.invertImageButton.clicked.connect(lambda: self.append_execution_queue('invert_image'))

        # Change image contrast
        self.invertedImageContrast.valueChanged.connect(lambda: self.imageInversion.change_contrast(self.invertedImageContrast.value()))

        # Change the image when the appropriate option is changed
        self.invTabImgType.currentIndexChanged.connect(self.imageInversion.toggle_img_type)

        # Connect pBASEX basis set button
        self.openBasisSet.clicked.connect(self.select_basis_set)

        # Connect changes to the calibration
        self.ionMassCombo.valueChanged.connect(self.imageInversion.updateRadialDist)
        self.ionChargeCombo.valueChanged.connect(self.imageInversion.updateRadialDist)
        self.distTypeCombo.currentIndexChanged.connect(self.imageInversion.updateRadialDist)

    def background_tab(self):
        def toggle_background_scaling():
            self.customBgScale.setEnabled(not self.customBgScale.isEnabled())
            self.main_ToF.plot_tof()
            self.main_image.updateImage()

        # Set up background option connections
        self.applyBackground.stateChanged.connect(self.main_ToF.plot_tof)
        self.applyBackground.stateChanged.connect(self.main_image.updateImage)
        self.customBgScale.valueChanged.connect(self.main_ToF.plot_tof)
        self.customBgScale.valueChanged.connect(self.main_image.updateImage)
        self.defaultBgScale.stateChanged.connect(toggle_background_scaling)

        # Change background image contrast
        self.bgIonImageContrast.valueChanged.connect(lambda: self.main_image.background.change_contrast(self.bgIonImageContrast.value()))

        # Connect transpose
        self.transpose.stateChanged.connect(self.main_image.background.process_image_transpose)

    ############################################
    # File IO
    ############################################
    def select_file(self, fileTextBox):
        # Set the file type (either All PImMS or dat)
        file_type_list = ['All PImMS (*.bin *.h5)', 'Binary files (*.bin)', 'h5 files (*.h5)', 'Dat files (*.dat)', 'All files (*.*)']
        file_type = file_type_list[self.last_file_type]  + ';;' + ';;'.join(file_type_list[:self.last_file_type] + file_type_list[1 + self.last_file_type:])

        fname = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open file', self.cur_path, file_type)
        
        # If a file is chosen, update the display and save the default path
        if fname[0] != '':
            try:
                fileTextBox.setText(fname[0])
                self.cur_path = os.path.dirname(fname[0])
            except TypeError:
                if fname[0] != []:
                    fileTextBox.setText('; '.join(fname[0]))
                    self.cur_path = os.path.dirname(fname[0][-1])

                    # Update the default directories only if they have not been set yet
                    if self.save_window.cur_path == '':
                        self.save_window.set_default_path(default_path = self.cur_path)
                    if self.load_parameters.cur_path == '':
                        self.load_parameters.set_default_path(self.cur_path)

        try:
            # Set the same default file type next time the window is opened
            self.last_file_type = file_type_list.index(fname[1])
        except ValueError:
            pass

    def select_folder(self):
        foldername = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choose folder', self.cur_path)

        # If a folder is chosen, update the display and save the default path
        if foldername != '':
            self.centroidFolderName.setText(foldername)
            self.cur_path = foldername

    def save_output_file(self, data, type):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, f'Save {type}', self.cur_path, "Dat files (*.dat);;All files (*.*)")[0]
        
        # Process cancel
        if fname == '':
            return

        # Save the data
        np.savetxt(fname, data, delimiter='\t')

    def select_basis_set(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose basis',
                        os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Inversion_functions', 'Basis_sets'),
                        "Basis sets (*.h5);;All files (*.*)")
        
        if fname[0] != '':
            self.pBASEXBasisSet.setText(fname[0])

    def open_save_window(self):
        # Show the window and make it appear at the front
        self.save_window.show()
        self.save_window.activateWindow()

    def load_energy_calibration_file(self, load_from_parameter_file=False, cali_data=None):
        if load_from_parameter_file:
            cali_loaded = True
        else:
            # Open the load calibration dialogue. cali_loaded will be 1 if a calibration selected, zero otherwise.
            caliDialogue = load_calibration()
            cali_loaded = caliDialogue.exec()
            try:
                cali_data = caliDialogue.cali_data
            except AttributeError:
                # Calibration box closed, so do nothing
                return

        if cali_loaded:
            # Add the calibration information to the image inversion class
            self.imageInversion.radial_dist_converter.cali_data = cali_data

            # Update the calibration name display
            self.currentCalibration.setText(cali_data['name'])

            # Enable the distribution selector
            self.distTypeCombo.setEnabled(True)

            try:
                # Enable saving of calibrated radial distributions
                self.imageInversion.inversion_class
                if not self.save_window.calibration_loaded:
                    self.save_window.enable_cali_saves()
            except AttributeError:
                pass

            # Make sure the appropriate save buttons are set to be enabled
            self.save_window.calibration_loaded = True

    def open_load_parameters_window(self):
        # Show the window and make it appear at the front
        self.load_parameters.show()
        self.load_parameters.activateWindow()
    ############################################

    def closeEvent(self, event):
        # Close any subwindows
        self.save_window.close()
        self.load_parameters.close()

    
        
        

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    app.exec()

if __name__ == '__main__':
    main()