import pimmsread
from timeit import default_timer
import pyqtgraph as pg
from PyQt6.QtCore import *
import numpy as np

class image_plotter():
    def __init__(self, main_variables):
        # Add the widget
        self.widget = main_variables.ionImageWidget

        # Make sure the image remains square
        self.widget.setAspectLocked()

        self.widget.disableAutoRange()

        # Note that the ROIs are not drawn initially
        self.circle_ROI_enabled = False
        self.rect_ROI_enabled = False

        # Add imageHoverCoords display widget to the class
        self.imageHoverCoords = main_variables.imageHoverCoords
        
        # Connect the section which displays the hover location on mouse move
        self.widget.scene().sigMouseMoved.connect(self.update_mouse_location)

        # Add widgets from the main class that need to be updated
        self.acqCycles = main_variables.acqCycles
        self.compTime = main_variables.compTime
        self.loadingWidget = main_variables.loadingWidget

        self.transposeImage = False

        # Add ROI
        main_variables.circleROlButton.clicked.connect(lambda: self.add_ROI('circle'))
        main_variables.rectROIButton.clicked.connect(lambda: self.add_ROI('rect'))

        # Add bars for use in inversion
        self.add_bars(main_variables.xCentrePos, main_variables.yCentrePos)

        # Add toggle for bar visibility
        main_variables.toggleCrosshairs.stateChanged.connect(self.toggle_bar_visibility)

        self.background = background_image(main_variables)


    def add_bars(self, spinX, spinY):
        # Generate limit bars
        self.vbar = pg.InfiniteLine(pos=161.5, angle=90, movable=True, bounds=(0,324), pen={'color':'w', 'width': 1})
        self.hbar = pg.InfiniteLine(pos=161.5, angle=0, movable=True, bounds=(0,324), pen={'color':'w', 'width': 1})

        # Add limit bars to the plot and make sure they stay at the front
        self.widget.addItem(self.vbar); self.widget.addItem(self.hbar)
        self.vbar.setZValue(1); self.hbar.setZValue(1)

        # Set the bars invisible by default
        self.vbar.setVisible(False); self.hbar.setVisible(False)

        # Process the moving of the bars
        self.vbar.sigPositionChangeFinished.connect(lambda: self.bar_moved(self.vbar.value(), spinX))
        self.hbar.sigPositionChangeFinished.connect(lambda: self.bar_moved(self.hbar.value(), spinY))

        # Process change in centre from the spin box
        spinX.valueChanged.connect(lambda: self.centre_changed(spinX.value(), 'x'))
        spinY.valueChanged.connect(lambda: self.centre_changed(spinY.value(), 'y'))

    def bar_moved(self, bar_value, spinWidget):
        # Update the appropriate spin widget to display the slider value
        # Should be rounded to the nearest 0.5
        spinWidget.setValue(round(2 * bar_value, 0) / 2)

    def centre_changed(self, value, bar_axis):
        # Update the appropriate slider to display the spin widget value
        if bar_axis == 'x':
            self.vbar.setValue(value)
        else:
            self.hbar.setValue(value)

    def toggle_bar_visibility(self, state):
        self.vbar.setVisible(state != 0)
        self.hbar.setVisible(state != 0)

    def update_mouse_location(self, mouse_location):
        # Get the position and add to the display. Note the -0.5 to make the number match with the indexing.
        image_position = self.widget.plotItem.vb.mapSceneToView(mouse_location)
        try:
            intensity = self.ionImage[int(round(image_position.x())), int(round(image_position.y()))]
            self.imageHoverCoords.setText(f'({round(image_position.x(), 1)}, {round(image_position.y(), 1)}) | val.: {round(intensity, 4)}')

        except AttributeError:
            # Case where no image plotted
            self.imageHoverCoords.setText(f'({round(image_position.x(), 1)}, {round(image_position.y(), 1)})')

        except IndexError:
            # Case where hovering outside image limits within image widget
            pass

    def change_contrast(self, contrast=1.):
        # The contrast should be stored in the class and changed as required
        self.contrast = contrast

        try:
            max = self.ionImage.max() * self.contrast
            min = self.ionImage.min() * self.contrast
            
            if max > abs(min) / 10:
                # Assume a positive signal (zero negatives for the display)
                self.colourBar.setLevels(values=(0,max))

            elif max == min:
                # Make sure there is a colour bar when the limits are the same
                self.colourBar.setLevels(values=(min,min+0.001 * self.contrast))

            else:
                # If the biggest signal is negative, assume this is intentional
                self.colourBar.setLevels(values=(min,max))
        except AttributeError:
            pass


    def process_image_transpose(self):
        try:
            self.transposeImage = not self.transposeImage

            if self.transposeImage:
                self.img.setImage(self.ionImage.T)
            else:
                self.img.setImage(self.ionImage)

        except AttributeError:
            pass


    def updateImage(self):
        try:
            # Apply the background subtraction if required
            self.ionImage = self.background.apply_background(self.signalIonImage, float(self.acqCycles.text()))
            
        except AttributeError:
            # Case where no signal image has been plotted yet
            return

        try:
            # Set the new image
            if self.transposeImage: self.img.setImage(self.ionImage.T)
            else:                   self.img.setImage(self.ionImage)

            # Update the colour bar if it exists
            self.colourBar.setImageItem(self.img)

        except AttributeError:
            # Create image data type
            if self.transposeImage: self.img = pg.ImageItem(image = self.ionImage)
            else:                   self.img = pg.ImageItem(image = self.ionImage)

            # Add ion image to widget
            self.widget.addItem(self.img)

            # Otherwise add colour bar
            self.colourBar = self.widget.addColorBar(self.img, colorMap='inferno', interactive=False)
    
        # Set the range to the image size
        imageShape = self.ionImage.shape
        self.widget.setRange(xRange=(0,imageShape[0]), yRange=(0,imageShape[1]))
        self.widget.setLimits(xMin=0, xMax=imageShape[0], yMin=0, yMax=imageShape[1])

        try:
            self.change_contrast(self.contrast)
        except AttributeError:
            self.change_contrast()


    def add_ROI(self, ROI_type):
        # Draw the appropriate ROI
        if ROI_type == 'circle' and self.circle_ROI_enabled == False:
            self.circle_ROI = pg.CircleROI((120,120), (30,30), removable=True, invertible=True)
            self.widget.addItem(self.circle_ROI)
            self.circle_ROI_enabled = True

            # Add connection to remove the ROI
            self.circle_ROI.sigRemoveRequested.connect(lambda: self.remove_ROI('circle'))

        elif ROI_type == 'rect' and self.rect_ROI_enabled == False:
            self.rect_ROI = pg.RectROI((120,120), (30,30), removable=True, invertible=True)
            self.widget.addItem(self.rect_ROI)
            self.rect_ROI_enabled = True

            # Add connection to remove the ROI
            self.rect_ROI.sigRemoveRequested.connect(lambda: self.remove_ROI('rect'))

    def remove_ROI(self, ROI_type):
        if ROI_type == 'circle':
            self.widget.removeItem(self.circle_ROI)
            self.circle_ROI_enabled = False

        elif ROI_type == 'rect':
            self.widget.removeItem(self.rect_ROI)
            self.rect_ROI_enabled = False


    def update(self, ion_image, acq_cycles, bg_ion_image, bg_acq_cycles, comp_time):
        # Set the computation time and acquisition cycles
        self.acqCycles.setText(acq_cycles)
        self.compTime.setText(comp_time)

        # Add the ion image to the plotter class
        self.signalIonImage = ion_image

        if bg_acq_cycles not in ['0', '-1']:
            # Add the background info to the background class
            self.background.bgIonImage = bg_ion_image
            self.background.bgAcqCycles.setText(bg_acq_cycles)

            self.background.updateImage()

        # Plot the image
        self.updateImage()

    def getIonImage(self, fname, bg_fname, t1, t2):
        # Show the loading widget
        self.loadingWidget.show()

        self.thread = QThread()

        # Initialise the worker class
        self.worker = ionImage_Qthread()

        # Add the required variables to the class
        self.worker.fname = fname
        self.worker.bg_fname = bg_fname
        self.worker.t1 = t1
        self.worker.t2 = t2

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



class ionImage_Qthread(QObject):
    output = pyqtSignal(object, str, object, str, str)
    finished = pyqtSignal()

    def run(self):
        # Start timer
        start = default_timer()

        # No need to continue if no files selected
        if self.fname == '':
            self.finished.emit()
            return

        subset_image, no_cycles = self.read_image(self.fname.split(';'))

        # Read background if file name specified
        if self.bg_fname != '':
            bg_subset_image, bg_no_cycles = self.read_image(self.bg_fname.split(';'))

        else:
            # No background to read
            bg_subset_image = None; bg_no_cycles = '-1'
            
        # End timer
        end = default_timer()

        # Output the signal and background images
        self.output.emit(subset_image, str(no_cycles), bg_subset_image, str(bg_no_cycles), str(round(end - start,2)) + ' s')

        self.finished.emit()

    def read_image(self, fname_list):
        for fname in fname_list:
            fname = fname.strip()

            try:
                # Generate the ToF
                if fname[-4:] == '.bin':
                    pimms_file = pimmsread.pimms(fname)
                elif fname[-3:] == '.h5':
                    pimms_file = pimmsread.pimms_h5(fname)
                else:
                    # Read a ddt file
                    try:
                        subset_image += np.loadtxt(fname, delimiter='\t')
                        no_cycles += 1
                    except NameError:
                        subset_image = np.loadtxt(fname, delimiter='\t')
                        no_cycles = 1
                    continue
                
                # Read the PImMS file
                if self.t1 > self.t2:
                    pimms_file.read_image_data_subset_single_image(self.t2, self.t1)
                else:
                    pimms_file.read_image_data_subset_single_image(self.t1, self.t2)

                # Increment the variables
                try:
                    subset_image += pimms_file.subset_image
                    no_cycles += pimms_file.no_frames
                except NameError:
                    subset_image = pimms_file.subset_image
                    no_cycles = pimms_file.no_frames

            except FileNotFoundError:
                pass
            except OSError:
                pass
            except IndexError:
                pass

        return subset_image, no_cycles



class background_image():
    def __init__(self, main_variables):
    # Set pointers to the appropriate variables for bg subtraction
        self.applyBackground = main_variables.applyBackground
        self.defaultBgScale = main_variables.defaultBgScale
        self.customBgScale = main_variables.customBgScale

        self.bgImageWidget = main_variables.bgIonImageWidget

        # Make sure the image remains square
        self.bgImageWidget.setAspectLocked()
        self.bgImageWidget.disableAutoRange()

        self.bgAcqCycles = main_variables.bgAcqCycles

        self.transposeImage = False


    def updateImage(self):
        # Remove previous image
        try:
            self.bgImageWidget.removeItem(self.img)
        except AttributeError:
            pass

        # Create image data type
        self.img = pg.ImageItem(image = self.bgIonImage)

        # Add ion image to widget
        self.bgImageWidget.addItem(self.img)

        try:
            # Update the colour bar if it exists
            self.colourBar.setImageItem(self.img)

        except AttributeError:
            # Otherwise add colour bar
            self.colourBar = self.bgImageWidget.addColorBar(self.img, colorMap='inferno', interactive=False)

        # Set the range to the image size
        imageShape = self.bgIonImage.shape
        self.bgImageWidget.setRange(xRange=(0,imageShape[0]), yRange=(0,imageShape[1]))
        self.bgImageWidget.setLimits(xMin=0, xMax=imageShape[0], yMin=0, yMax=imageShape[1])

        try:
            self.change_contrast(self.contrast)
        except AttributeError:
            self.change_contrast()


    def change_contrast(self, contrast=1.):
        # The contrast should be stored in the class and changed as required
        self.contrast = contrast

        try:
            max = self.bgIonImage.max() * self.contrast
            self.colourBar.setLevels(values=(0,max))
        except AttributeError:
            pass


    def process_image_transpose(self):
        try:
            self.transposeImage = not self.transposeImage

            if self.transposeImage:
                self.img.setImage(self.bgIonImage.T)
            else:
                self.img.setImage(self.bgIonImage)

        except AttributeError:
            pass

    
    def apply_background(self, signalIonImage, acqCycles):
        # Apply the appropriate background subtraction if requested
        if self.applyBackground.isChecked():
            try:
                if self.defaultBgScale.isChecked():
                    # Scale background according to number of acquisition cycles
                    self.customBgScale.setValue(acqCycles / float(self.bgAcqCycles.text()))
                
                # Scale background according to provided ratio
                ionImage = signalIonImage - self.bgIonImage * self.customBgScale.value()

            except (ZeroDivisionError, AttributeError):
                # Case where no background is loaded
                ionImage = signalIonImage

        else:
            # No background subtraction
            ionImage = signalIonImage

        return ionImage