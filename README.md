# PImMS-image-analysis
GUI to process PImMS datasets. To begin, ensure all required packages are installed, then run ```PImMS_image_analysis.py```

For reference, the PImMS camera is an event-driven camera which records (x,y,t) datapoints. This means we have information on the arrival time and position of ions measured in an experiment, from which we can gain insight into the dynamics of the process we are studying.

## Getting started - Reading data and plotting an image
The code can read in both binary and h5 format PImMS data, along with tab-delimited image data. The input file can be entered at the top of the window, either by typing or by using the file dialogue, opened by pressing the button next to the file name field. By default, only binary (.bin) and h5 (.h5) files are shown, but this can be changed.

Once a PImMS input file is chosen, the next step is to plot the time-of-flight (ToF) spectrum. This is done by pressing the <b>Plot ToF</b> button. After the data is loaded, the graph will populate. The vertical lines can then be moved to select one of the peaks, each of which corresponds to a different ionic species.

Next, an image can be plotted (this is the first step if a tab-delimited (.dat) file was selected). Clicking <b>Plot Image</b> will populate the image with either the image corresponding to the time range selected in the ToF spectrum above (PImMS data), or the image (for a tab-delimited input). The image can be transposed and the contrast changed using the appropriate fields to the right.

## Background subtraction
A background file can be selected using the Background tab. If a background file is selected, when the buttons on the first tab are pressed, the background file will also be loaded, and subtracted from the result when the Apply background checkbox is checked. The weighting of the subtraction is set by the ratio of number of acquisition cycles between the two datasets by default, but can also be manually changed. The background ToF and ion image for the current ion are shown in the Background tab.

## Image inversion
Typically, PImMS datasets are recorded in such a way that three-dimensional (3D) scattering distributions are recorded as two-dimensional (2D) projections. However, we want to know the original 3D scattering distribution, as this contains information on the velocity of the ions formed. Fortunately, the physics of the experiments often means that an axis of cylindrical symmetry is present in the plane of the image, which allows image inversion algorithms, such as the Abel inversion, to be employed. These algorithms determine the central slice of the 3D distribution from the 2D projection and, since there is an axis of cylindrical symmetry, this central slice fully describes the 3D distribution. More information can be found in the PyAbel documentation.

To invert an image, the centre of the image from the Plot ToF range tab needs to be selected. To do this, check the Toggle crosshairs box, and move the crosshairs to the centre of the ion image. Unless simulated data is used, this is very unlikely to be the centre of the detector. A detector mask can also be applied, which restricts the points which are considered when symmetrising the molecule. Symmetrisation is just the process of folding the image both horizontally and vertically into a single quadrant. This utilises the symmetry of the images to increase the signal-to-noise ratio. The detector mask can be applied, for example, if the image is highly off-centre, and the distribution extends beyond the edge of the detector in some places.

In the invert tab, we can then simply click the <b>Invert images</b> button, and an inverted image and radial distribution will be plotted. The inversion parameters can be changed on the right, with BASEX, rBASEX, pBASEX, Hansen Law and Three-point being included by default. The parameters for these can be found in the PyAbel and pBASEX package documentation. There is also the option of changing the number of beta parameters used for the fitting, using Max beta and use odd beta. These are not plotted anywhere at present, but can be saved using the File menu.

By default the radial distribution is plotted, but a calibration can be added to generate a velocity, momentum or kinetic energy distribution. To enable these distributions to be explored, a calibration is required. By clicking <b>Load Calibration</b>, a calibration can be selected, or a new one created. If adding a new calibration, provide a name, the maximum radius at which the calibration is valid, whether to interpolate at low radius, and the fitting equation. This can be determined either experimentally by running benchmarking experiments, or estimated using SIMION simulations. A typical fitting equation would be of the order of 5E-3 * r ** 2. For velocity and momentum, ensure the mass and charge are correct. Also, note that the distribution does not automatically update on loading a new calibration, so make sure to either swapping to another distibution type and back, or invert the image again.

## Mass calibration
While the arrival time of ions is measured by PImMS, these arrival can be converted to mass-to-charge (m/z), i.e. a mass spectrum can be generated. By adding the arrival time and known m/z to the table on the left of the Mass calibration tab, then clicking <b>Plot calibration</b>, an m/z will be determined for each arrival time, and the mass spectrum plotted at the bottom of the tab. If the calibration is reasonable, the fit on the right should show a straight line, passing through the points that have been defined.

Note that on other tabs, the m/z value is printed rather than plotted.

## Centroiding
When running experiments, the detector is set up in such a way that a single pixel triggers multiple pixels on the PImMS camera. These have a spread in both space and time. Centroiding allows these clusters of pixel events to be combined into a single (x,y,t) coordinate for the ion. The algorithm used here is as described in the D.Phil. thesis of Craig Slater, University of Oxford (2013).

To centroid a single file, press the <b>Centroid</b> button. This will centroid the current input file, and save out a centroided PImMS file (binary format) if Save output is checked. The extension _+XX_miniY will be appended to the file name, where XX is the time spread and Y is the minimum cluster size. The time spread should be set such that little change is seen on increasing the value further. The default values should be fine in most cases.

If multiple files need to be centroided, there is also the option to centroid a folder. By adding a folder path at the bottom of the tab and clicking the <b>Centroid folder</b> button, any PImMS files which do not already have an existing centroided file with the same parameters will be centroided (files ending _+XX_miniY.bin are ignored).

## Saving outputs
Description to be added
