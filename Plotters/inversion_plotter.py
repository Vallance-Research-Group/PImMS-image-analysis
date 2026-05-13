from timeit import default_timer
import pyqtgraph as pg
from PyQt6.QtCore import *
import Inversion_functions.Inversion_methods as inversion_methods
from Inversion_functions.dist_calibration import radial_dist_unit_conversion
import numpy as np

class inversion_plotter():

    def __init__(self, main_variables):
        # Initialise the detector mask
        self.detectorMask = detector_mask()

        # Add the required GUI pointers to the class
        self.compTime = main_variables.compTime
        self.loadingWidget = main_variables.loadingWidget
        self.xCentrePos = main_variables.xCentrePos
        self.yCentrePos = main_variables.yCentrePos
        self.inversionMethodCombo = main_variables.inversionMethod
        self.maxBetaCombo = main_variables.maxBeta
        self.useOddBeta = main_variables.useOddBeta
        self.transposeInputImage = main_variables.transpose
        self.basisFunctionOptionWidget = main_variables.basisFunctionOptionWidget
        self.invTabImgType = main_variables.invTabImgType

        # Options for specific inversion methods
        self.basisFunctionWidthBASEX = main_variables.basisFunctionWidthBASEX
        self.regStrengthBASEX = main_variables.regStrengthBASEX
        self.regStrengthRBASEX = main_variables.regStrengthRBASEX
        self.regMethodComboRBASEX = main_variables.regMethodComboRBASEX
        self.regStrengthPBASEX = main_variables.regStrengthPBASEX
        self.pBASEXBasisSet = main_variables.pBASEXBasisSet

        # Add the plot widgets to the class
        self.invertedImageWidget = main_variables.invertedImageWidget
        self.radialDistributionWidget = main_variables.radialDistributionWidget

        # Keep the inverted image square
        self.invertedImageWidget.setAspectLocked()

        # Add invImageHoverCoords display widget to the class
        self.invImageHoverCoords = main_variables.invImageHoverCoords
        
        # Connect the section which displays the hover location on mouse move
        self.invertedImageWidget.scene().sigMouseMoved.connect(self.update_mouse_location)

        # Add the ion image class in, as we need to access some of its variables to sync things
        self.ionImageClass = main_variables.main_image

        # Add labels to the radial distribution
        self.radialDistributionWidget.setLabel("bottom", "Radius / px")
        self.radialDistributionWidget.setLabel("left", "Intensity / arb. units")

        # Set the limits of the view
        self.radialDistributionWidget.setLimits(xMin=-1, xMax=200)

        # Change the options displayed when the inversion method is changed
        self.inversionMethodCombo.currentIndexChanged.connect(self.update_inversion_option_display)

        # Copy the pointer to the combo box
        self.distTypeCombo = main_variables.distTypeCombo

        # Options for the different x axis labels
        self.label_options = {'Radial': 'Radius / px', 'Velocity': 'Velocity / ms<sup>-1</sup>', 'Momentum': 'Momentum / kgms<sup>-1</sup>', 'Energy': 'Energy / eV'}

        # Set up the class to carry out velocity/momentum/energy calibration
        self.radial_dist_converter = radial_dist_unit_conversion(main_variables.ionMassCombo, main_variables.ionChargeCombo)


    def toggle_detector_mask(self, ionImageWidget):
        self.detectorMask.toggle(ionImageWidget)

    def update_inversion_option_display(self):
        new_method = self.inversionMethodCombo.currentText()
        if new_method == 'BASEX':
            self.basisFunctionOptionWidget.setCurrentIndex(0)
        elif new_method == 'rBASEX':
            self.basisFunctionOptionWidget.setCurrentIndex(1)
        elif new_method == 'pBASEX':
            self.basisFunctionOptionWidget.setCurrentIndex(2)


    def update_mouse_location(self, mouse_location):
        # Get the position and intensity (if an image has been plotted), and add to the display
        image_position = self.invertedImageWidget.plotItem.vb.mapSceneToView(mouse_location)
        try:
            intensity = self.ionImage[int(round(image_position.x())), int(round(image_position.y()))]
            self.invImageHoverCoords.setText(f'({round(image_position.x(), 1)}, {round(image_position.y(), 1)}) | val.: {round(intensity, 4)}')

        except AttributeError:
            # Case where no image plotted
            self.invImageHoverCoords.setText(f'({round(image_position.x(), 1)}, {round(image_position.y(), 1)})')

        except IndexError:
            # Case where hovering outside image limits within image widget
            pass


    def change_contrast(self, contrast=1.):
        # The contrast should be stored in the class and changed as required
        self.contrast = contrast

        try:
            max = self.invertedImage.max() * self.contrast
            self.colourBar.setLevels(values=(0,max))
        except AttributeError:
            pass


    def updateImage(self):
        # Remove previous image
        try:
            self.invertedImageWidget.removeItem(self.img)
        except AttributeError:
            pass

        # Create image data type
        self.img = pg.ImageItem(image = self.invertedImage)

        # Add ion image to widget
        self.invertedImageWidget.addItem(self.img)

        try:
            # Update the colour bar if it exists
            self.colourBar.setImageItem(self.img)

        except AttributeError:
            # Otherwise add colour bar
            self.colourBar = self.invertedImageWidget.addColorBar(self.img, colorMap='inferno', interactive=False)

        # Set the range to the image size
        imageShape = self.invertedImage.shape
        self.img.setRect(-0.5, -0.5, imageShape[0], imageShape[1])
        self.invertedImageWidget.setRange(xRange=(-0.5, imageShape[0]-0.5), yRange=(-0.5, imageShape[1]-0.5))
        self.invertedImageWidget.setLimits(xMin=-0.5, xMax=imageShape[0]-0.5, yMin=-0.5, yMax=imageShape[1]-0.5)

        try:
            self.change_contrast(self.contrast)
        except AttributeError:
            self.change_contrast()

        self.invertedImageWidget.autoRange()

        # Plot the radial distribution
        self.updateRadialDist()

    def updateRadialDist(self):
        # Get the requested distribution type
        dist_type = self.distTypeCombo.currentText()

        try:
            # Get the calibrated distribution
            x_coords, y_coords = self.radial_dist_converter(self.inversion_class.radius,
                                                        self.inversion_class.radial_intensity[0],
                                                        type=dist_type,
                                                        normalise=True)
            
            # Set the limits of the view
            self.radialDistributionWidget.setLimits(xMin=-x_coords.max()/200, xMax=x_coords.max() * 1.005)

        except AttributeError:
            return # No inversion has been carried out yet

        # Plot the data
        try:
            self.plot_line.setData(x_coords, y_coords)
        except AttributeError:
            self.plot_line = self.radialDistributionWidget.plot(x_coords,
                                                y_coords,
                                                pen={'color':'k', 'width': 1})

        # Update the x axis label
        self.radialDistributionWidget.setLabel("bottom", self.label_options[dist_type])

        self.radialDistributionWidget.autoRange()

    def update(self, inversion_class, comp_time):
        # Set the computation time and acquisition cycles
        self.compTime.setText(comp_time)

        # Add the inversion class
        self.inversion_class = inversion_class

        # Retranspose the images
        self.inversion_class.symmetrised_image = np.array([im.T for im in self.inversion_class.symmetrised_image])
        self.inversion_class.inverted_image = np.array([im.T for im in self.inversion_class.inverted_image])

        # Set the ion image
        if self.invTabImgType.currentIndex() == 0:
            self.invertedImage = self.inversion_class.inverted_image[0]
        else:
            self.invertedImage = self.inversion_class.symmetrised_image[0]

        # Plot the image
        self.updateImage()


    def toggle_img_type(self):
        try:
            # Update the image
            if self.invTabImgType.currentIndex() == 0:
                self.invertedImage = self.inversion_class.inverted_image[0]
            else:
                self.invertedImage = self.inversion_class.symmetrised_image[0]
            self.updateImage()

        except AttributeError:
            pass


    def invert_image(self):
        # Show the loading widget
        self.loadingWidget.show()

        self.thread = QThread()

        # Initialise the worker class
        self.worker = inversion_Qthread()

        # Add the required variables to the class
        self.worker.inversion_method = self.inversionMethodCombo.currentText()
        self.worker.beta_order = self.maxBetaCombo.value()
        self.worker.odd_beta = self.useOddBeta.isChecked()
        self.worker.image_centre = (self.yCentrePos.value(), self.xCentrePos.value())
        self.worker.detector_mask = self.detectorMask.detector_mask
        self.detectorMask.get_centre_and_radius()
        self.worker.mask_centre = self.detectorMask.centre
        self.worker.mask_radius = self.detectorMask.radius

        try:
            # The transpose is intentionally different here, to make sure the symmetry axis for inversion
            # is correct. The images are all retransposed when returned to the update function
            if self.transposeInputImage.isChecked():
                self.worker.raw_image = np.array([self.ionImageClass.ionImage])
            else:
                self.worker.raw_image = np.array([self.ionImageClass.ionImage.T])

            if self.worker.inversion_method == 'BASEX':
                self.worker.sigma = self.basisFunctionWidthBASEX.value()
                self.worker.reg_strength = self.regStrengthBASEX.value()
            elif self.worker.inversion_method == 'rBASEX':
                self.worker.reg_method = self.regMethodComboRBASEX.currentText()
                self.worker.reg_strength = self.regStrengthRBASEX.value()
            elif self.worker.inversion_method == 'pBASEX':
                self.worker.reg_strength = self.regStrengthPBASEX.value()
                self.worker.basis_set = self.pBASEXBasisSet.text()

        except AttributeError:
            self.worker.raw_image = np.array((-1))

        # Move the worker to the thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.output.connect(self.update)

        # Hide the loading widget after the calculation is done
        self.thread.finished.connect(lambda: self.loadingWidget.hide())

        # Start the thread
        self.thread.start()

        return self.thread

class inversion_Qthread(QObject):
    output = pyqtSignal(object, str)
    finished = pyqtSignal()

    def run(self):
        # Exit if no image plotted yet
        if self.raw_image.sum() == -1:
            self.finished.emit()
            return

        # Start timer
        start = default_timer()
    
        # Initialise the appropriate inversion class
        if self.inversion_method == 'BASEX':
            inversion_class = inversion_methods.basex()
            inversion_class.sigma = self.sigma
            inversion_class.reg_strength = self.reg_strength

        elif self.inversion_method == 'rBASEX':
            inversion_class = inversion_methods.rbasex()
            inversion_class.reg_method = self.reg_method
            inversion_class.reg_strength = self.reg_strength

        elif self.inversion_method == 'Hansen-Law':
            inversion_class = inversion_methods.hansen_law()

        elif self.inversion_method == 'Three-point':
            inversion_class = inversion_methods.three_point()

        elif self.inversion_method == 'None':
            inversion_class = inversion_methods.no_inversion()

        elif self.inversion_method == 'pBASEX':
            inversion_class = inversion_methods.pbasex_caller()
            inversion_class.reg_strength = self.reg_strength
            inversion_class.basis_set = self.basis_set
            try:
                inversion_class.load_basis_set()
            except FileNotFoundError:
                print('Please select basis function.')
                print('pBASEX basis functions can be generated using Inversion_functions/pbasex_save_gData_(basis_functions).py.')
                self.finished.emit()
                return
            except KeyError:
                print('Please select basis function')
                print('pBASEX basis functions can be generated using Inversion_functions/pbasex_save_gData_(basis_functions).py.')
                self.finished.emit()
                return

        else:
            print('Warning: Chosen inversion method not supported. Radial distribution given (not inverted).')
            inversion_class = inversion_methods.no_inversion()

        # Set the ion image to invert
        inversion_class.set_image(self.raw_image)
        inversion_class.image_centre = self.image_centre

        # Set the detector mask as appropriate
        if self.detector_mask:
            inversion_class.apply_detector_mask = True
            inversion_class.mask_centre = self.mask_centre
            inversion_class.mask_radius = self.mask_radius

        # Add the beta parameters (for use when required)
        inversion_class.odd_beta = self.odd_beta
        # Need to make sure the beta order is even if odd beta not ticked
        if not self.odd_beta and self.beta_order % 2 == 1:
            inversion_class.beta_order = self.beta_order - 1
        else:
            inversion_class.beta_order = self.beta_order

        # Run the inversion
        inversion_class()

        # End timer
        end = default_timer()

        self.output.emit(inversion_class, str(round(end - start,2)) + ' s')

        self.finished.emit()

class detector_mask():
    def __init__(self):
        # Initialise variables
        self.detector_mask = False
        self.pos = (11.5,11.5)
        self.size = (300,300)

    def toggle(self, imageWidget):
        # Invert detector mask state
        self.detector_mask = not self.detector_mask

        if self.detector_mask:
            # Add a circle ROI (first tuple is origin (bottom left), second is size)
            self.circle_ROI = pg.CircleROI(self.pos, self.size, removable=True, invertible=False)

            self.circle_ROI.setZValue(1)
            imageWidget.addItem(self.circle_ROI)

            # Add connection to remove the ROI
            self.circle_ROI.sigRemoveRequested.connect(lambda: self.toggle_detector_mask(imageWidget))

        else:
            # Get the parameters so it initialises in the same place
            self.pos = self.circle_ROI.pos()
            self.size = self.circle_ROI.size()

            # Remove the circle ROI
            imageWidget.removeItem(self.circle_ROI)

    def get_centre_and_radius(self):
        try:
            self.pos = self.circle_ROI.pos()
            self.size = self.circle_ROI.size()
        except AttributeError:
            pass

        self.radius = self.size[0] / 2
        # Note these are the other way round than might be expected, as the image is transposed prior to inversion
        self.centre = (self.pos[1] + self.radius, self.pos[0] + self.radius)

            
        

