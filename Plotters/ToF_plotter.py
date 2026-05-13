import pyqtgraph as pg
import pimmsread
from timeit import default_timer
from PyQt6.QtCore import *
import numpy as np



class ToF_plotter():
    def __init__(self, main_variables, spinOne, spinTwo):
        # Add the widgets
        self.widget = main_variables.ToFWidget
        self.spinOne = spinOne
        self.spinTwo = spinTwo

        # Add the widgets that need to be updated
        self.acqCycles = main_variables.acqCycles
        self.bgAcqCycles = main_variables.bgAcqCycles
        self.compTime = main_variables.compTime

        # Set the limits and the initial view
        self.widget.setLimits(xMin=0, xMax=4095)
        self.widget.setRange(xRange=(0,4095))

        # Plot axes on top and right
        self.widget.showAxis('right')
        self.widget.showAxis('top')

        # Generate limit bars
        self.vbar = pg.InfiniteLine(pos=1000, angle=90, movable=True, bounds=(0,4095))
        self.vbar2 = pg.InfiniteLine(pos=3000, angle=90, movable=True, bounds=(0,4095))

        # Add limit bars to the plot
        self.widget.addItem(self.vbar)
        self.widget.addItem(self.vbar2)

        # ToF limits moved
        self.vbar.sigPositionChangeFinished.connect(lambda: self.vbar_moved(self.vbar.value(), spinOne))
        self.vbar2.sigPositionChangeFinished.connect(lambda: self.vbar_moved(self.vbar2.value(), spinTwo))

        self.plot_line = self.widget.plot([0], [0.5], pen={'color':'k', 'width': 1})

        # ToF limits changed
        main_variables.ToF_limit_one.valueChanged.connect(lambda: self.limits_changed(main_variables.ToF_limit_one.value(), 1))
        main_variables.ToF_limit_two.valueChanged.connect(lambda: self.limits_changed(main_variables.ToF_limit_two.value(), 2))

        # Define the time bins
        self.x_values = np.arange(0,4096)

        # Set up the background ToF widget
        # Set the limits and the initial view
        main_variables.bgToFWidget.setLimits(xMin=0, xMax=4095)
        main_variables.bgToFWidget.setRange(xRange=(0,4095))
        self.bg_plot_line = main_variables.bgToFWidget.plot(self.x_values, np.zeros(4096), pen={'color':'k', 'width': 1})

        # Set pointers to the appropriate variables for bg subtraction
        self.applyBackground = main_variables.applyBackground
        self.defaultBgScale = main_variables.defaultBgScale
        self.customBgScale = main_variables.customBgScale


    def get_tof(self, fname, bg_fname, loadingWidget):
        # Show the loading widget
        loadingWidget.show()

        self.thread = QThread()

        # Initialise the worker class
        self.worker = ToF_Qthread()

        # Add the required variables to the class
        self.worker.fname = fname

        # Only load the background again if the file name has been changed
        try:
            if self.bg_fname != bg_fname:
                self.worker.bg_fname = bg_fname
            else:
                # Make sure a ToF has been plotted before not loading the background
                self.tof
                self.worker.bg_fname = ''

        except AttributeError:
            self.worker.bg_fname = bg_fname

        self.bg_fname = bg_fname

        # Move the worker to the thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.output.connect(self.update)

        # Hide the loading widget after the calculation is done
        self.thread.finished.connect(lambda: loadingWidget.hide())

        # Start the thread
        self.thread.start()

        return self.thread


    def update(self, tof, acq_cycles, bg_tof, bg_acq_cycles, comp_time):
        # Add ToF to the class
        self.signal_tof = tof

        # Set the computation time and acquisition cycles
        self.acqCycles.setText(acq_cycles)
        self.compTime.setText(comp_time)

        # # Plot the ToF
        # self.plot_line.setData(self.x_values, tof)

        # Set and plot the background ToF if it has been plotted
        if bg_acq_cycles not in ['0', '-1']:
            self.bg_tof = bg_tof
            self.bgAcqCycles.setText(bg_acq_cycles)

            self.bg_plot_line.setData(self.x_values, bg_tof)

        # Plot the ToF
        self.plot_tof()


    def plot_tof(self):
        try:
            # Apply the appropriate background subtraction if requested
            if self.applyBackground.isChecked():
                try:
                    if self.defaultBgScale.isChecked():
                        # Scale background according to number of acquisition cycles
                        self.customBgScale.setValue(float(self.acqCycles.text()) / float(self.bgAcqCycles.text()))
                    
                    # Scale background according to provided ratio
                    self.tof = self.signal_tof - self.bg_tof * self.customBgScale.value()

                except (ZeroDivisionError, AttributeError):
                    # Case where no background is loaded
                    self.tof = self.signal_tof

            else:
                self.tof = self.signal_tof

            # Plot the ToF
            self.plot_line.setData(self.x_values, self.tof)
        
        except AttributeError:
            # This is to account for the case where there is no signal ToF
            pass


    def vbar_moved(self, vbar_limit, spinWidget):
        # Update the appropriate spin widget to display the slider value
        spinWidget.setValue(int(np.round(vbar_limit)))

    def limits_changed(self, value, vbar_pointer):
        # Update the appropriate slider to display the spin widget value
        try:
            if vbar_pointer == 1:
                self.vbar.setValue(value)
                self.tofLimOneMz.setText(str(self.m_q[self.spinOne.value()]))
            else:
                self.vbar2.setValue(value)
                self.tofLimTwoMz.setText(str(self.m_q[self.spinTwo.value()]))

        except AttributeError:
            pass

    def set_mass_calibration(self, min_time, m_q):
        # Make an array which will contain all the m / z
        self.m_q = np.zeros(4096) - 1
        self.m_q[min_time:] = np.round(m_q, 1)

        # Set the values of the display
        self.tofLimOneMz.setText(str(self.m_q[self.spinOne.value()]))
        self.tofLimTwoMz.setText(str(self.m_q[self.spinTwo.value()]))


class ToF_Qthread(QObject):
    output = pyqtSignal(object, str, object, str, str)
    finished = pyqtSignal()

    def run(self):
        # Start timer
        start = default_timer()

        # Read the signal ToF
        tof, no_cycles = self.read_tof(self.fname.split(';'))

        # Return if there is an invalid file selected
        if no_cycles == -1:
            return

        # Read the background ToF
        bg_tof, bg_no_cycles = self.read_tof(self.bg_fname.split(';'))

        # End timer
        end = default_timer()

        if no_cycles > 0 and bg_no_cycles > 0:
            self.output.emit(tof, str(no_cycles), bg_tof, str(bg_no_cycles), str(round(end - start,2)) + ' s')
        elif no_cycles > 0:
            self.output.emit(tof, str(no_cycles), -1, str(0), str(round(end - start,2)) + ' s')

        self.finished.emit()


    def read_tof(self, fname_list):
        # Initialise storage variables
        no_cycles = 0
        tof = np.zeros(4096)

        for fname in fname_list:
            fname = fname.strip()
            # Iterate through all files 
            try:
                # Generate the ToF
                if fname[-4:] == '.bin':
                    pimms_file = pimmsread.pimms(fname)
                elif fname[-3:] == '.h5':
                    pimms_file = pimmsread.pimms_h5(fname)
                else:
                    self.finished.emit()
                    return -1, -1
                    
                pimms_file.read_tof_only()

                tof += pimms_file.tof
                no_cycles += pimms_file.no_frames
                
            except FileNotFoundError:
                pass
            except OSError:
                pass

        return tof, no_cycles