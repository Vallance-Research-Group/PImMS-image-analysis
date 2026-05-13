import numpy as np
from numba import jit
import pimmsread
import os
from timeit import default_timer
from threading import Thread
from glob import glob
from PyQt6.QtCore import *
import pyqtgraph as pg

# This centroiding function checks for ALL connected ion hits arriving within the time window.
# Note that the checks are carried out repeatedly, so early hits not connected to the original
# hit may be included. There is a sequential version below.
@jit(nopython=True)
def centroiding_function(cycleData, tSpread, minClusterSize, clusterSizeArray):
    # Get the number of hits
    no_hits = len(cycleData)

    # # Define a cluster image
    clusterImage = np.zeros((324,324), dtype=np.uint16)

    # Define a centroided data array
    centroidedData = np.zeros((int(no_hits / minClusterSize + 0.5),3), dtype=np.uint16)

    # Define the cluster number
    clusterNumber = 0

    # Define the ion number
    ionNumber = 0

    # Initialise an array to account for which hits have been accounted for
    hit_accounted_for = np.zeros(no_hits)

    # For each ion hit
    for i in range(no_hits):
        # If ion hit already accounted for, move onto next ion
        if hit_accounted_for[i] == 1:
            continue

        # Set cluster size to one
        clusterSize = 1

        # Increment the cluster number
        clusterNumber += 1

        # Set x_sum, y_sum and t_sum to x, y, 1
        x_sum = cycleData[i,0]
        y_sum = cycleData[i,1]
        t_sum = 1

        # Add the cluster to the cluster image
        clusterImage[cycleData[i,0],cycleData[i,1]] = clusterNumber

        # Get the initial time and calculate the final time
        initialTime = cycleData[i,2]
        finalTime = initialTime + tSpread

        # Initialise foundNeighbour
        foundNeighbour = True

        # Look through the remaining ion hits for neighbouring hits
        while foundNeighbour == True:
            # Reset the foundNeighbour flag
            foundNeighbour = False

            for j in range(i+1, no_hits):
                # Check if hit already accounted for
                if hit_accounted_for[j] == 1:
                    continue

                # Check the time is in the appropriate range (sorted by time, so no need to check for initial time)
                if cycleData[j,2] > finalTime:
                    continue

                # Get the x and y coordinates for ease of use
                j_x = cycleData[j,0]; j_y = cycleData[j,1]

                # Check the region of the image to see if any neighbouring pixels are included
                if np.sum(clusterImage[j_x-1:j_x+2, j_y-1:j_y+2] == clusterNumber) > 0:
                    # Deal with the case where the same pixel is triggered twice (shouldn't be from the same ion hit)
                    if clusterImage[j_x, j_y] == clusterNumber:
                        continue

                    # Increment the cluster size
                    clusterSize += 1

                    # Update the cluster image
                    clusterImage[j_x, j_y] = clusterNumber

                    # Set that the hit is accounted for
                    hit_accounted_for[j] = 1

                    # Set that a neighbouring ion hit has been found
                    foundNeighbour = True

                    # Increment x_sum, y_sum and t_sum (see C. Slater's thesis for the dividing by t)
                    time = cycleData[j,2] - initialTime + 1
                    x_sum += cycleData[j,0] / time
                    y_sum += cycleData[j,1] / time
                    t_sum += 1 / time

        if clusterSize >= minClusterSize:
            # Add the cluster to the centroided data array if it's a cluster
            centroidedData[ionNumber, 0] = int(x_sum / t_sum + 0.5)
            centroidedData[ionNumber, 1] = int(y_sum / t_sum + 0.5)
            centroidedData[ionNumber, 2] = initialTime

            # Increment the ion number
            ionNumber += 1

        # Update the cluster size array
        clusterSizeArray[clusterSize - 1] += 1

    return centroidedData[:ionNumber]


# Sequential version of the centroiding code. From the original ion hit, checks each arrival time in
# turn, adding to the cluster where appropriate. This is usually preferable.
# To check all times instead, use the code above.
@jit(nopython=True)
def centroiding_function_sequential(cycleData, tSpread, minClusterSize, clusterSizeArray):
    # Get the number of hits
    no_hits = len(cycleData)

    # # Define a cluster image
    clusterImage = np.zeros((324,324), dtype=np.uint16)

    # Define a centroided data array
    centroidedData = np.zeros((int(no_hits / minClusterSize + 0.5),3), dtype=np.uint16)

    # Define the cluster number
    clusterNumber = 0

    # Define the ion number
    ionNumber = 0

    # Initialise an array to account for which hits have been accounted for
    hit_accounted_for = np.zeros(no_hits)

    # For each ion hit
    for i in range(no_hits):
        # If ion hit already accounted for, move onto next ion
        if hit_accounted_for[i] == 1:
            continue

        # Set cluster size to one
        clusterSize = 1

        # Increment the cluster number
        clusterNumber += 1

        # Set x_sum, y_sum and t_sum to x, y, 1
        x_sum = cycleData[i,0]
        y_sum = cycleData[i,1]
        t_sum = 1

        # Add the cluster to the cluster image
        clusterImage[cycleData[i,0],cycleData[i,1]] = clusterNumber

        # Get the initial time and calculate the final time
        initialTime = cycleData[i,2]
        finalTime = initialTime + tSpread

        # Define the current time and the found neighbour flag
        _time = initialTime
        foundNeighbour = True

        # Define the first hit to check and initalise j
        first_hit_check = i + 1
        j = i + 1

        # Look through time bins sequentially
        while True:
            if foundNeighbour == False:
                # Stop the iteration at the final allowed time
                if _time == finalTime:
                    break

                # Increment the current time to consider
                _time += 1

                # Stop unnecessary iterations when current time has exceeded the maximum time
                if _time > cycleData[-1,2]:
                    break

                # Set the first hit to check to the last j value (which should be defined
                # by timebin > _time from the previous loop)
                first_hit_check = j

            # Reset the foundNeighbour flag
            foundNeighbour = False

            for j in range(first_hit_check, no_hits):
                # Times are sorted, so fine to exit for loop once current time is exceeded
                if cycleData[j,2] > _time:
                    break

                # Check if hit already accounted for
                elif hit_accounted_for[j] == 1:
                    continue

                # Get the x and y coordinates for ease of use
                j_x = cycleData[j,0]; j_y = cycleData[j,1]

                # Check the region of the image to see if any neighbouring pixels are included
                if np.sum(clusterImage[j_x-1:j_x+2, j_y-1:j_y+2] == clusterNumber) > 0:
                    # Deal with the case where the same pixel is triggered twice (shouldn't be from the same ion hit)
                    if clusterImage[j_x, j_y] == clusterNumber:
                        continue

                    # Increment the cluster size
                    clusterSize += 1

                    # Update the cluster image
                    clusterImage[j_x, j_y] = clusterNumber

                    # Set that the hit is accounted for
                    hit_accounted_for[j] = 1

                    # Set that a neighbouring ion hit has been found
                    foundNeighbour = True

                    # Increment x_sum, y_sum and t_sum (see C. Slater's thesis for the dividing by t)
                    time = cycleData[j,2] - initialTime + 1
                    x_sum += cycleData[j,0] / time
                    y_sum += cycleData[j,1] / time
                    t_sum += 1 / time

        if clusterSize >= minClusterSize:
            # Add the cluster to the centroided data array if it's a cluster
            centroidedData[ionNumber, 0] = int(x_sum / t_sum + 0.5)
            centroidedData[ionNumber, 1] = int(y_sum / t_sum + 0.5)
            centroidedData[ionNumber, 2] = initialTime

            # Increment the ion number
            ionNumber += 1

        # Update the cluster size array
        if clusterSize <= 100:
            clusterSizeArray[clusterSize - 1] += 1

    return centroidedData[:ionNumber]


class centroid_folder():

    def __init__(self, input_folder):
        self.input_folder = input_folder
        self.folder = True

    def get_files_to_centroid(self, tspread, mincluster, max_cycles):
        # Work out which files to centroid in the file
        # Get list of all binary files
        all_files = glob(os.path.join(self.input_folder, '*.bin')) +\
            glob(os.path.join(self.input_folder, '*.h5'))

        # Get the list centroided with the current parameters and all centroided files
        cur_centroided = glob(os.path.join(self.input_folder, f'*_+{str(tspread).zfill(2)}_mini{str(mincluster)}.bin')) +\
            glob(os.path.join(self.input_folder, f'*_+{str(tspread).zfill(2)}_mini{str(mincluster)}.h5'))
        all_centroided = glob(os.path.join(self.input_folder, f'*_+*_mini*.bin')) +\
            glob(os.path.join(self.input_folder, f'*_+*_mini*.h5'))

        # Get the list of current files (for the electron rig)
        current_files = glob(os.path.join(self.input_folder, '*_current.bin'))

        # Remove the centroided files from the all file list
        non_centroided_files = [x for x in all_files if x not in all_centroided]

        # Remove the current files from the non-centroided file list
        non_centroided_files = [x for x in non_centroided_files if x not in current_files]

        # Remove the files which have already been centroided with the current conditions (h5 and bin)
        non_centroided_files = [x for x in non_centroided_files if f'{x[:-3]}_+{str(tspread).zfill(2)}_mini{str(mincluster)}.bin' not in cur_centroided]
        non_centroided_files = [x for x in non_centroided_files if f'{x[:-3]}_+{str(tspread).zfill(2)}_mini{str(mincluster)}.h5' not in cur_centroided]
        non_centroided_files = [x for x in non_centroided_files if f'{x[:-4]}_+{str(tspread).zfill(2)}_mini{str(mincluster)}.h5' not in cur_centroided]
        self.files_to_centroid = [x for x in non_centroided_files if f'{x[:-4]}_+{str(tspread).zfill(2)}_mini{str(mincluster)}.bin' not in cur_centroided]


    def run(self, tspread=8, mincluster=2, max_cycles=50000000, save_data=True):
        if self.folder:
            self.get_files_to_centroid(tspread, mincluster, max_cycles)
        else:
            self.files_to_centroid = [self.input_folder]

        if __name__ != '__main__':
            #########
            # Run the centroiding process in a separate thread if using the GUI
            #########
            # https://realpython.com/python-pyqt-qthread/#worker-threads
            # Start the QThread
            self.thread = QThread()

            # Initialise the worker class
            self.worker = run_centroiding_Qthread()

            # Add the required variables to the class
            self.worker.file_list = self.files_to_centroid
            self.worker.tspread = tspread
            self.worker.mincluster = mincluster
            self.worker.max_cycles = max_cycles
            self.worker.save_data = save_data

            # Move the worker to the thread
            self.worker.moveToThread(self.thread)

            # Connect signals and slots
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # Start the thread
            self.thread.start()

        else:
            
            for _file in self.files_to_centroid:
                cur_file = centroid(_file)
                cur_file.centroid_file(tspread, mincluster, max_cycles)
    


class run_centroiding_Qthread(QObject):
    fileSignal = pyqtSignal(str)
    output = pyqtSignal(str, str, float, object)
    finished = pyqtSignal()

    def run(self):
        total_files = len(self.file_list)

        # Reset the 
        self.output.emit('', '', 0., np.zeros(50))

        # Iterate through each file and run the centroiding algorithm
        for i, _file in enumerate(self.file_list):
            if _file.split('.')[-1] == 'bin':
                self.fileSignal.emit(_file[:-4] + f'_+{str(self.tspread).zfill(2)}_mini{str(self.mincluster)}.bin')
            else:
                self.fileSignal.emit(_file[:-3] + f'_+{str(self.tspread).zfill(2)}_mini{str(self.mincluster)}.bin')

            cur_file = centroid(_file)

            # Start timer
            start = default_timer()

            # Centorid
            cur_file.centroid_file(self.tspread, self.mincluster, self.max_cycles, self.save_data)

            # End timer
            end = default_timer()

            self.output.emit(str(cur_file.no_cycles), f'{round(end-start,2)} s', (i + 1) / total_files * 100., cur_file.clusterSizeArray)

        self.finished.emit()


class centroid():
    def __init__(self, fname):
        self.fname = fname
        if self.fname[-4:] == '.bin':
            self.pimms_file = pimmsread.pimms(fname)
        else:
            self.pimms_file = pimmsread.pimms_h5(fname)

    def centroid_file(self, tspread=8, mincluster=2, max_cycles=50000000, save_data=True):
        # Set the parameters
        self.time_spread = tspread
        self.min_cluster_size = mincluster
        if self.fname[-4:] == '.bin':
            outFile = self.fname[:-4] + f'_+{str(self.time_spread).zfill(2)}_mini{str(self.min_cluster_size)}.bin'
        else:
            outFile = self.fname[:-3] + f'_+{str(self.time_spread).zfill(2)}_mini{str(self.min_cluster_size)}.bin'

        # Define the cluster size array
        self.clusterSizeArray = np.zeros(100)

        # Set up the generator
        data_gen = self.pimms_file.read_pimms_file()

        # Read up to the maximum number of acquisition cycles to centroid
        if save_data:
            with open(outFile, 'wb') as f:
                try:
                    for i in range(max_cycles):
                        # Get data for the next acquisition cycle and sort
                        self.cycleData = next(data_gen)
                        self.cycleData = self.cycleData[np.argsort(self.cycleData[:,2])]

                        # Run centroiding on acquisition cycle
                        clusterData = self.centroid_cycle()

                        # Save the data
                        np.array([len(clusterData),3]).astype('int32').tofile(f)
                        clusterData.tofile(f)

                    # Need to increment by one if not stopped by an error to get the correct
                    # number of cycles
                    i += 1

                except ValueError:
                    pass

                except StopIteration:
                    pass

        else:
            try:
                for i in range(max_cycles):
                    # Get data for the next acquisition cycle and sort
                    self.cycleData = next(data_gen)
                    self.cycleData = self.cycleData[np.argsort(self.cycleData[:,2])]

                    # Run centroiding on acquisition cycle
                    self.centroid_cycle()

                # Need to increment by one if not stopped by an error to get the correct
                # number of cycles
                i += 1

            except ValueError:
                pass

            except StopIteration:
                pass

        # Store the number of acquisition cycles
        self.no_cycles = i

    
    def centroid_cycle(self):
        # Choose the appropriate centroiding function
        # centroidedData = centroiding_function(self.cycleData, self.time_spread, self.min_cluster_size, self.clusterSizeArray)
        centroidedData = centroiding_function_sequential(self.cycleData, self.time_spread, self.min_cluster_size, self.clusterSizeArray)

        return centroidedData


class centroid_widgets():
    def __init__(self, main_variables):
        # Add widgets to the class
        self.clusterSizeWidget = main_variables.clusterSizeWidget
        self.acqCycles = main_variables.acqCycles
        self.compTime = main_variables.compTime
        self.progressBar = main_variables.centroidProgressBar
        self.centroidOutFile = main_variables.centroidOutFile

        # Set the limit on x
        self.clusterSizeWidget.setLimits(xMin=0.5, yMin=0)
        self.clusterSizeWidget.setRange(xRange=(0.5,40))

        # Plot axes on top and right
        self.clusterSizeWidget.showAxis('right')
        self.clusterSizeWidget.showAxis('top')

        # Initialise the bar graph
        self.clustersize_array = np.zeros(5)
        self.plot_bargraph()


    def plot_bargraph(self):
        # Remove a previous version from the widget if already present
        try:
            self.clusterSizeWidget.removeItem(self.bar_graph)
        except AttributeError:
            pass

        # Generate the bar graph
        self.bar_graph = pg.BarGraphItem(x=np.arange(1,len(self.clustersize_array) + 1), height=self.clustersize_array, width=0.8, brush='r')

        # Add to the widget
        self.clusterSizeWidget.addItem(self.bar_graph)

    def update_centroid_plots(self, acq_cycles, computation_time, completion_percentage, clustersize_array):
        # Update various display boxes
        self.progressBar.setValue(int(np.round(completion_percentage)))

        if acq_cycles == '':
            # No need to update anything else if the calculation has just started
            return

        self.acqCycles.setText(acq_cycles)
        self.compTime.setText(computation_time)

        # Update clustersize array
        self.clustersize_array = clustersize_array

        # Plot the cluster size distribution
        self.plot_bargraph()
        

    def update_output_file_display(self, outFile):
        self.centroidOutFile.setText(outFile)

    def run_single_file(self, main_variables):
        # Get the file name
        file_name = main_variables.fileName.text()

        # Do nothing if no folder has been chosen
        if file_name == '':
            return 0

        # Define the centroiding folder class as required
        try:
            self.centroidFolder.input_folder = file_name
        except AttributeError:
            self.centroidFolder = centroid_folder(file_name)

        # Specify that this is not a folder
        self.centroidFolder.folder = False

        # Centorid the file
        self.centroidFolder.run(int(main_variables.centroidTSpread.value()),
                                int(main_variables.centroidMinClusterSize.value()),
                                int(main_variables.centroidCyclesToProcess.value()),
                                bool(main_variables.centroidSave.isChecked()))

        # Make sure the centroid plots update
        self.centroidFolder.worker.output.connect(self.update_centroid_plots)

        # Make sure the output file updates
        self.centroidFolder.worker.fileSignal.connect(self.update_output_file_display)

        # Display the loading widget as appropriate
        main_variables.loadingWidget.show()
        self.centroidFolder.thread.finished.connect(lambda: main_variables.loadingWidget.hide())

        return self.centroidFolder.thread

    def run_all_folders(self, main_variables):
        # Get the folder name
        folder_name = main_variables.centroidFolderName.text()

        # Do nothing if no folder has been chosen
        if folder_name == '':
            return 0

        # Define the centroiding class as required
        try:
            self.centroidFolder.input_folder = folder_name
        except AttributeError:
            self.centroidFolder = centroid_folder(folder_name)

        # Specify we are centroiding a folder
        self.centroidFolder.folder = True

        # Centroid the folder
        self.centroidFolder.run(int(main_variables.centroidTSpread.value()),
                                int(main_variables.centroidMinClusterSize.value()),
                                int(main_variables.centroidCyclesToProcess.value()),
                                bool(main_variables.centroidSave.isChecked()))

        # Make sure the centroid plots update
        self.centroidFolder.worker.output.connect(self.update_centroid_plots)

        # Make sure the output file updates
        self.centroidFolder.worker.fileSignal.connect(self.update_output_file_display)

        # Disable the tab navigation so that other buttons cannot be pressed in the meantime
        main_variables.tabWidget.setEnabled(False)
        main_variables.loadingWidget.show()
        self.centroidFolder.thread.finished.connect(lambda: main_variables.tabWidget.setEnabled(True))
        self.centroidFolder.thread.finished.connect(lambda: main_variables.loadingWidget.hide())

        return self.centroidFolder.thread


if __name__ == '__main__':
    # fname = os.path.expanduser(r'~\Documents\Python Scripts\Image_processing\Full analysis suite\Centroiding\Test data\20190807_003.bin')
    # start = default_timer()
    # centroid(fname).centroid_file()
    # end = default_timer()
    # print(str(round(end - start, 2)) + ' s')

    centroid_folder(os.path.expanduser(r'~\Documents\Python Scripts\Image_processing\Full analysis suite\Centroiding\Test data')).run()