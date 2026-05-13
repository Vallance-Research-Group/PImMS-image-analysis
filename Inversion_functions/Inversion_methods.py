import numpy as np
import abel
import os
from Inversion_functions.gData import loadG
from pbasex import pbasex
from quadrant import resizeFolded


class inversion_methods():
    def __init__(self, inversion_type, *, direction='inverse'):
        self.method = inversion_type
        self.direction = direction
        
        # Add defaults for the inversion
        self.symmetry_axis = (0,1)
        self.use_quadrants = (True,True,True,True)
        self.apply_detector_mask = False
        self.mask_centre = (162,162)
        self.mask_radius=162
        self.zero_neg = False
        self.image_centre = (161.5,161.5)
        self.odd_beta = False
        self.beta_order = 2


    def set_image(self, raw_image):
        self.raw_image = raw_image

    def transform(self, folded_image):
        #Add more inversion methods in as required
        if self.method == 'basex':
            inverted_image = abel.basex.basex_transform(folded_image, direction=self.direction, **self.transform_options)
        elif self.method == 'hansen-law':
            inverted_image = abel.hansenlaw.hansenlaw_transform(folded_image, direction=self.direction, **self.transform_options)
        elif self.method == 'three-point':
            inverted_image = abel.dasch.three_point_transform(folded_image, direction=self.direction, **self.transform_options)
        elif self.method == 'rbasex':
            # Note that the 'folded' image provided here is actually the symmetrised image
            inverted_image, distr = abel.rbasex.rbasex_transform(folded_image, direction=self.direction, **self.transform_options)

            # Extract r, I, and beta from the distr variable
            distr_out = distr.rIbeta()
            beta = np.concatenate((distr_out[0].reshape((1,-1)),distr_out[2:]),axis=0)

            # Add labels to the top of each column (-1 for r, corresponding n for Bn for others)
            order = self.transform_options['order']
            if self.transform_options['odd']:
                beta_labels = np.array([-1] + [i for i in range(1,order+1)]).reshape((-1,1))
            else:
                beta_labels = np.array([-1] + [i for i in range(2,order+1,2)]).reshape((-1,1))

            self.beta.append(np.concatenate((beta_labels, beta),axis=1))

        return inverted_image

    def invert_image(self):
        # Need to be able to invert both delay-dependent and delay-independent data
        if len(self.raw_image.shape) == 2:
            self.raw_image = self.raw_image[None,:,:]

        self.symmetrised_image = []
        self.inverted_image = []
        self.radial_intensity = []
        self.beta = []

        for i, raw_image in enumerate(self.raw_image):
            folded_image, fold_segments = fold_image(raw_image, self.image_centre, self.symmetry_axis, self.use_quadrants,\
                                                        self.apply_detector_mask, self.mask_centre, self.mask_radius)

            # Zero any negative values in the symmetrised image if desired
            if self.zero_neg:
                folded_image[folded_image < 0] = 0

            self.symmetrised_image.append(self.reconstruct_image(folded_image, fold_segments))

            if self.method == 'rbasex':
                # rBASEX uses (and returns)  a full-size image, rather than a quadrant
                self.inverted_image.append(self.transform(self.symmetrised_image[-1]))
            else:
                inverted_image = self.transform(folded_image)
                self.inverted_image.append(self.reconstruct_image(inverted_image, fold_segments))

                self.get_beta(self.inverted_image[i])

            try:
                dr = self.transform_options['dr']
            except KeyError:
                dr = 0.5

            #Get the radial distribution
            radius, radial_intensity = abel.tools.vmi.angular_integration_3D(self.inverted_image[i], dr=dr)

            self.radial_intensity.append(radial_intensity)

        # This will be the same for all images, as no parameters are changed and the images are the same size
        self.radius = radius


    def get_beta(self, inverted_image):
        # This function is for use with the methods which do not automatically
        # return beta parameters (e.g. BASEX, Hansen-Law, 3-point)

        # Extract r, I, and beta from the distr variable
        distr_out = abel.tools.vmi.rIbeta(inverted_image, origin='cc', rmax='MIN',
                                          order=self.beta_order, window=1, odd=self.odd_beta)

        # Remove the radial distribution column
        beta = np.concatenate((distr_out[0].reshape((1, -1)), distr_out[2:]), axis=0)

        # Add labels to the top of each column (-1 for r, corresponding n for Bn for others)
        order = self.beta_order
        if self.odd_beta:
            beta_labels = np.array([-1] + [i for i in range(1, order + 1)]).reshape((-1, 1))
        else:
            beta_labels = np.array([-1] + [i for i in range(2, order + 1, 2)]).reshape((-1, 1))
        
        self.beta.append(np.concatenate((beta_labels, beta), axis=1))


    def reconstruct_image(self, image, fold_segs):
        #Deal with the case of a two segment and four segment image separately
        if fold_segs == 2:
            #Need an image one under twice as wide as the half. One less as the
            #0 column is treated as the central column
            reconstructed_image = np.zeros([image.shape[0], image.shape[1]*2-1])

            #Assign the image to reconstructed image
            reconstructed_image[:,image.shape[1]-1:] = image
            reconstructed_image[:,:image.shape[1]] = np.fliplr(image)

        else:
            #Want a square result. Minus one required as described above
            quadrant_dim = np.max(image.shape)
            reconstructed_image = np.zeros([quadrant_dim*2-1, quadrant_dim*2-1])

            #Assign the image to the reconstructed image
            reconstructed_image[quadrant_dim-1:quadrant_dim-1+image.shape[0],\
                    quadrant_dim-1:quadrant_dim-1+image.shape[1]] = image

            reconstructed_image[quadrant_dim-image.shape[0]:quadrant_dim,\
                    quadrant_dim-1:quadrant_dim-1+image.shape[1]] = np.flipud(image)

            reconstructed_image[quadrant_dim-1:quadrant_dim-1+image.shape[0],\
                    quadrant_dim-image.shape[1]:quadrant_dim] = np.fliplr(image)

            reconstructed_image[quadrant_dim-image.shape[0]:quadrant_dim,\
                    quadrant_dim-image.shape[1]:quadrant_dim] = np.fliplr(np.flipud(image))

        return reconstructed_image


class rbasex(inversion_methods):
    def __init__(self):
        super().__init__('rbasex')

        self.basis_path = os.path.dirname(os.path.realpath(__file__)) + '/Basis_sets'
        # Make the directory to store the basis sets in
        if os.path.isdir(self.basis_path) == False:
            os.mkdir(self.basis_path)

    def __call__(self):
        # Set the transform options to pass to PyAbel
        try:
            self.transform_options = dict(order=self.beta_order, odd=self.odd_beta,
                                            reg=(self.reg_method, self.reg_strength),
                                            basis_dir=self.basis_path)
        except AttributeError:
            self.transform_options = dict(order=2, odd=False,
                                            reg=('L2', 0),
                                            basis_dir=self.basis_path)

            print('Parameters missing! Using default values.')

        self.invert_image()


class hansen_law(inversion_methods):
    def __init__(self):
        super().__init__('hansen-law')

        # Set the transform options to pass to PyAbel
        self.transform_options = dict(dr=0.5)

    def __call__(self):
        self.invert_image()


class basex(inversion_methods):
    def __init__(self):
        super().__init__('basex')

        self.basis_path = os.path.dirname(os.path.realpath(__file__)) + '/Basis_sets'
        # Make the directory to store the basis sets in
        if os.path.isdir(self.basis_path) == False:
            os.mkdir(self.basis_path)

    def __call__(self):
        # Set the transform options to pass to PyAbel
        try:
            self.transform_options = dict(sigma=self.sigma, reg=self.reg_strength,
                                            correction=True, basis_dir=self.basis_path)
        except AttributeError:
            self.transform_options = dict(sigma=3, reg=0,
                                            correction=True, basis_dir=self.basis_path)
            print('Parameters missing! Using default values.')

        self.invert_image()


class three_point(inversion_methods):
    def __init__(self):
        super().__init__('three-point')

        self.basis_path = os.path.dirname(os.path.realpath(__file__)) + '/Basis_sets'
        # Make the directory to store the basis sets in
        if os.path.isdir(self.basis_path) == False:
            os.mkdir(self.basis_path)

        # Set the transform options to pass to PyAbel
        self.transform_options = dict(basis_dir=self.basis_path)

    def __call__(self):
        self.invert_image()


class no_inversion(inversion_methods):
    def __init__(self):
        super().__init__(None)

    def __call__(self):
        if len(self.raw_image.shape) == 2:
            self.raw_image = self.raw_image[None,:,:]

        # Initialise the variables
        self.symmetrised_image = []
        self.radial_intensity = []

        for raw_image in self.raw_image:
            # Generate the symmetrised image
            folded_image, fold_segments = fold_image(raw_image, self.image_centre, self.symmetry_axis, self.use_quadrants,\
                                                        self.apply_detector_mask, self.mask_centre, self.mask_radius)

            # Zero any negative values in the symmetrised image if desired
            if self.zero_neg:
                folded_image[folded_image < 0] = 0

            self.symmetrised_image.append(self.reconstruct_image(folded_image, fold_segments))
            
            self.radius, radial_intensity = abel.tools.vmi.angular_integration_2D(self.symmetrised_image[-1], dr=1.0)
            self.radial_intensity.append(radial_intensity)

        self.inverted_image = self.symmetrised_image


class pbasex_caller(inversion_methods):
    def __init__(self):
        super().__init__('pbasex')

    def load_basis_set(self):
        # Load the basis set
        self.gData = loadG(self.basis_set, 1)

        try:
            self.basis_r = int(self.basis_set.split('Basis_sets')[-1].split('_')[1][1:])
        except ValueError:
            print('Radius cannot be read from pBASEX basis function')

    def __call__(self):
        self.symmetrised_image = []
        self.inverted_image = []
        self.radial_intensity = []
        self.beta = []

        for raw_image in self.raw_image:
            # Get folded image
            folded_image, _ = fold_image(raw_image,
                                            self.image_centre,
                                            symmetry_axis=self.symmetry_axis,
                                            use_quadrants=self.use_quadrants,
                                            apply_detector_mask=self.apply_detector_mask,
                                            mask_centre=self.mask_centre,
                                            mask_radius=self.mask_radius)

            # Make sure the folded image dimensions match those of the basis set
            folded_image = resizeFolded(folded_image, self.basis_r)

            # Zero any negative values in the symmetrised image if desired
            if self.zero_neg:
                folded_image[folded_image < 0] = 0

            self.symmetrised_image.append(self.reconstruct_image(folded_image, _))

            # Apply the pBASEX algorithm
            try:
                out = pbasex(folded_image.T, self.gData, make_images=True, regularization=self.reg_strength, alpha=1.0)
            except AttributeError:
                print('Warning: regularisation strength missing. Using no regularisation.')
                out = pbasex(folded_image.T, self.gData, make_images=True, regularization=0, alpha=1.0)
            # Note that out contains inv (inverted image), fit (fit of the original image),
            # E (Energy, adjusted using alpha), IE (intensity as a function of E), betas (Beta parameters as specified by l)

            # Set betas in same format as for other methods
            try:
                betas = np.concatenate((np.sqrt(out['E']).reshape((1, -1)), out['betas'].T), axis=0)
            except ValueError:
                betas = np.concatenate((np.sqrt(out['E']).reshape((1, -1)), out['betas'].T.reshape((1, -1))), axis=0)

            beta_labels = np.array([-1] + [2 * i + 2 for i in range(len(betas) - 1)]).reshape((-1, 1))
            self.beta.append(np.concatenate((beta_labels, betas), axis=1))

            # Add the inverted image
            self.inverted_image.append(out['inv'].T)

            #Get the radial distribution
            radius, radial_intensity = abel.tools.vmi.angular_integration_3D(self.inverted_image[-1], dr=0.5)

            self.radial_intensity.append(radial_intensity)

        # This will be the same for all images, as no parameters are changed and the images are the same size
        self.radius = radius

def fold_image(raw_image, img_centre, symmetry_axis,use_quadrants,\
apply_detector_mask, mask_centre, mask_radius):
    # Takes an image, image centre and directions to fold, folds the image and
    # returns the folded image. A mask can also be applied to remove any contribution
    # from outside the detector. Note it is always assumed that axis 0, defined
    # below, is an axis of symmetry (indeed it must be for the inversion method
    # to be used in the first place).
    #
    # Symmetry axis 0 is the vertical axis (axis of cylindrical symmetry) and
    # axis 1 is the horizontal axis (when data is ploted with the origin in the
    # bottom left corner of the image [origin='lower' in matplotlib]). Quadrants
    # are ordered from top right in an anticlockwise direction (so
    # theta = 0 -> pi/2, then theta = pi/2 -> pi etc.).
    #
    # The pyabel package treats the zero pixel as the central pixel. If the image
    # centre is set to an integer, this will be used as the central column. If
    # the image centre is set to, say, 161.5, a combination of columns 161 and 162
    # will be used as the central column

    def apply_mask(image):
        #Create a grid of x and y coordinates
        x,y = np.ogrid[:image.shape[0],:image.shape[1]]
        cx, cy = mask_centre[0], mask_centre[1]

        #Work out the r squaded value for each pixel
        r_squared = (x-cx)**2 + (y-cy)**2

        #Apply mask where radius greater than the size of the image
        image[np.where(r_squared > mask_radius**2)] = np.nan

        return image


    def folding_function(raw_image, img_centre, symmetry_axis, use_quadrants):
        class folder():
            def __init__(self, dim_zero, dim_one, fold_segments):
                #Define the folded image, and the number of nan in each pixel
                self.folded_image = np.zeros((dim_zero, dim_one))
                self.no_nan = np.zeros((dim_zero, dim_one))
                self.fold_segments = fold_segments

            def process_quadrant(self, data, use_quad):
                #Four quadrants, so up to four nan values in a pixel
                self.max_nan = 4

                #Assume that every point in the image is nan
                self.no_nan += 1

                #Check the quadrant is to be used
                if use_quad == False:
                    return

                #Adjust the number of nan array. We assumed that all data were nan,
                #so start by subtracting one from all points within the image bounds.
                #Then, add one back on anywhere there was a nan included in the data.
                self.no_nan[:data.shape[0],:data.shape[1]] -= 1
                nan_location_array = np.isnan(data)
                self.no_nan[:data.shape[0],:data.shape[1]] += nan_location_array.astype('uint8')

                #Set all nan equal to zero
                data[nan_location_array] = 0

                #Add in the new data
                self.folded_image[:data.shape[0], :data.shape[1]] += data


            def process_half(self, data, use_upper_quad, use_lower_quad):
                #Two halves, so up to two nan values in a pixel
                self.max_nan = 2

                if use_upper_quad and use_lower_quad:
                    #If using both quadrants, no change required
                    pass
                elif use_upper_quad or use_lower_quad:
                    if use_upper_quad == False:
                        #If not using upper quad
                        data[img_centre[0]:] = np.nan
                    else:
                        #If not using lower quad
                        data[:img_centre[0]] = np.nan
                else:
                    # Case where not using either quadrant making up the half
                    #Increment nan count on all pixels
                    self.no_nan += 1
                    return

                #Adjust the number of nan array. Add one to all points not included
                #in the current image, then add one for any nan in the data
                self.no_nan[:,data.shape[1]:] += 1
                nan_location_array = np.isnan(data)
                self.no_nan[:,:data.shape[1]] += nan_location_array.astype('uint8')

                #Set all nan equal to zero
                data[nan_location_array] = 0

                #Add in the new data
                self.folded_image[:, :data.shape[1]] += data


            def finalise_image(self):
                #When normalising, need a non-zero divisor
                self.no_nan[np.where(self.no_nan == self.max_nan)] = self.max_nan - 1

                #Divide by the number of image segments - the number of nans not contributing
                self.folded_image = np.divide(self.folded_image, self.max_nan - self.no_nan)


        #Get the dimensions of the image
        img_dim_zero, img_dim_one = raw_image.shape[0], raw_image.shape[1]

        #Find the dimensions of the largest potential quadrant (img_centre has
        #one added due to zero-indexing, floor is to deal with half-integer centre)
        quadrant_dim_zero = np.floor(np.max([img_centre[0]+1, img_dim_zero-img_centre[0]])).astype('uint16')
        quadrant_dim_one = np.floor(np.max([img_centre[1]+1, img_dim_one-img_centre[1]])).astype('uint16')

        #Need to account for the difference in behaviour if the image centre
        #is between pixels or on a pixel. The former case needs no modification
        #to img_centre, whereas the latter requires one to be added when
        #indexing from the bottom (e.g. raw_image[:img_centre[0] + 1]).
        #This is because the same pixels need tobe included on more than
        #one occasion at the centre when the centre in either dimension is
        #on a pixel
        if img_centre[0] % 1 == 0:
            centre_zero = 1
            img_centre = (int(img_centre[0]), img_centre[1])
        else:
            centre_zero = 0
            img_centre = (np.round(img_centre[0] + 0.5).astype('uint16'), img_centre[1])

        if img_centre[1] % 1 == 0:
            centre_one = 1
            img_centre = (img_centre[0], int(img_centre[1]))
        else:
            centre_one = 0
            img_centre = (img_centre[0], np.round(img_centre[1] + 0.5).astype('uint16'))

        #There is an error if only a single number is put in the symmetry axis
        #tuple. Redefine symmetry_axis if this is the case.
        try:
            1 in symmetry_axis
        except TypeError:
            if symmetry_axis == (0):
                symmetry_axis = (0,0)
            elif symmetry_axis == (1):
                symmetry_axis = (1,1)
            else:
                symmetry_axis = (0, 1)

        #If there is symmetric under reflection perpendicular to the axis of
        #cylindrical symmetry, fold image into quadrants
        if symmetry_axis == (0,1):
            folding_class = folder(quadrant_dim_zero, quadrant_dim_one, 4)

            #Process each of the four quadrants in turn
            folding_class.process_quadrant(raw_image[img_centre[0]:,\
                    img_centre[1]:],\
                    use_quadrants[0])
            folding_class.process_quadrant(np.fliplr(raw_image[img_centre[0]:,\
                    :img_centre[1] + centre_one]),\
                    use_quadrants[1])
            folding_class.process_quadrant(np.fliplr(np.flipud(raw_image[:img_centre[0] + centre_zero,\
                    :img_centre[1] + centre_one])),\
                    use_quadrants[2])
            folding_class.process_quadrant(np.flipud(raw_image[:img_centre[0] + centre_zero,\
                    img_centre[1]:]),\
                    use_quadrants[3])

        #If there is only an axis of cylindrical symmetry, fold image into a half
        #image. Still need to know quadrant_dim_zero for the use_quadrants bit.
        else:
            # Need to transpose the image to fold it properly. Leave in transposed state (as this is the correct orientation for inversion).
            if 1 in symmetry_axis:
                print('Warning: There is an issue with using horizontal symmetrisation at present, \
since the axis of cylindrical symmetry is then set to lie along this axis. Please avoid for now.')
                raw_image = raw_image.transpose()
                half_dim_zero = img_dim_one
                half_dim_one = quadrant_dim_zero
                img_centre = (img_centre[1], img_centre[0])
                centre_temp = centre_one
                centre_one = centre_zero
                centre_zero = centre_temp
                use_quadrants = (use_quadrants[0], use_quadrants[3], use_quadrants[2], use_quadrants[1])
            else:
                half_dim_zero = img_dim_zero
                half_dim_one = quadrant_dim_one

            folding_class = folder(half_dim_zero, half_dim_one, 2)

            # Process each half of the image
            folding_class.process_half(raw_image[:,img_centre[1]:],\
                    use_quadrants[0], use_quadrants[3])
            folding_class.process_half(np.fliplr(raw_image[:, :img_centre[1] + centre_one]),\
                    use_quadrants[1], use_quadrants[2])

        folding_class.finalise_image()

        return folding_class.folded_image, folding_class.fold_segments

    ###############################
    if apply_detector_mask == True:
        #Apply mask if required
        masked_image = apply_mask(raw_image)
        return folding_function(masked_image, img_centre, symmetry_axis, use_quadrants)

    return folding_function(raw_image, img_centre, symmetry_axis, use_quadrants)


if __name__=='__main__':
    import matplotlib.pyplot as plt

    data = np.loadtxt(r'C:\Users\chem-hert4067\Documents\Python Scripts\Image_processing\Data simulation\Simulated_data\beta_test_mass_beta_-1.dat', delimiter='\t')
    plt.figure()
    plt.imshow(data.T, origin='lower', cmap='inferno')

    test = rbasex()
    test.raw_image = data.T
    test.symmetry_axis=(1)
    test()

    plt.figure()
    plt.imshow(test.symmetrised_image[0], origin='lower', cmap='inferno')

    plt.figure()
    plt.imshow(test.inverted_image[0], origin='lower', cmap='inferno')

    plt.figure()
    plt.plot(test.radius, test.radial_intensity[0])

    plt.show()
