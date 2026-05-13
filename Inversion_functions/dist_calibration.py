import numpy as np


class radial_dist_unit_conversion:
    def __init__(self, ionMassCombo, ionChargeCombo):
        self.ionMassCombo = ionMassCombo
        self.ionChargeCombo = ionChargeCombo

    def apply_calibration(self, r):
        # Evaluate the calibration equation (which is a function of r)
        # Note there is a factor of q when carrying out the energy calibration, so multiply by charge
        calibrated_x = eval(self.cali_data['equation']) * self.ionChargeCombo.value()

        # Interpolate at low r if requested
        if self.cali_data['interpolate']:
            calibrated_x[:5] = np.linspace(0, calibrated_x[5], num=5, endpoint=False)

        return calibrated_x, self.cali_data['max_r']


    def fun_radial(self, radius, intensity, normalise, cut):
        # Remove data from before the cut
        intensity = intensity[radius >= cut]
        radius = radius[radius >= cut]

        # Normalise the intensity if required
        if normalise == True:
            integral = np.trapz(intensity, radius)
            if integral != 0:
                intensity /= integral

        # Return the distribution
        return radius, intensity

    def fun_energy(self, radius, intensity, normalise, cut):
        # Remove data from before the cut
        intensity = intensity[radius >= cut]
        radius = radius[radius >= cut]

        # Apply the energy calibration to the radial coordinates
        energy, max_r = self.apply_calibration(radius)

        # Remove data from after the max_val
        intensity = intensity[radius < max_r]
        energy = energy[radius < max_r]

        # Apply the Jacobian for radius to energy conversion (set term where dividing by zero to nan)
        intensity[1:] = np.divide(intensity[1:], np.sqrt(energy[1:]))
        intensity[0] = np.nan

        # Normalise the intensity if required
        if normalise == True:
            integral = np.trapz(intensity[1:], energy[1:])
            if integral != 0:
                intensity /= integral

        # Return the distribution
        return energy, intensity

    def fun_velocity(self, radius, intensity, normalise, cut):
        # Remove data from before the cut
        intensity = intensity[radius >= cut]
        radius = radius[radius >= cut]

        # Apply the energy calibration to the radial coordinates
        energy, max_r = self.apply_calibration(radius)

        # Remove data from after the max_val
        intensity = intensity[radius < max_r]
        energy = energy[radius < max_r]

        # Energy and mass constants
        eV_joules = 1.602176634e-19
        unit_mass = 1.6605390666e-27

        # Convert from energy units to velocity units
        factor = np.divide(np.sqrt(eV_joules), np.sqrt(unit_mass))
        velocity = np.sqrt(energy * 2 / self.ionMassCombo.value()) * factor
        
        # Normalise the intensity if required
        if normalise == True:
            integral = np.trapz(intensity, velocity)
            if integral != 0:
                intensity /= integral
            
        # Return the distribution
        return velocity, intensity

    def fun_momentum(self, radius, intensity, normalise, cut):
        # Get the velocity distribution
        velocity, intensity = self.fun_velocity(radius, intensity, normalise, cut)

        # Mass constant
        unit_mass = 1.6605390666e-27

        # Convert velocity to momentum
        momentum = velocity * self.ionMassCombo.value() * unit_mass

        # Normalise the intensity if required
        if normalise == True:
            integral = np.trapz(intensity, momentum) * 10 ** 22
            if integral != 0:
                intensity /= integral

        # Return the distribution
        return momentum, intensity

    def __call__(self, radius, intensity, *, type='radial',
                 normalise=True, cut_off_pixels=0):
        # Takes radius and the intensity at each radius, and converts to the
        # distribution specified by type. This can be radial, velocity,
        # momentum or energy. If normalise is set to True, the integrated intensity
        # is set to one. Cut off pixels removes data from any pixels with radius
        # less than this from the distribution.
        
        # Get the appropriate function according to the calibration required
        calibration_fun = getattr(self, 'fun_' + type.lower(), None)

        # Run the function
        if calibration_fun is not None:
            radius, intensity = calibration_fun(radius, intensity, normalise, cut_off_pixels)
        else:
            print('Invalid distribution type. Plotting radial distribution.')
            radius, intensity = self.fun_radial(radius, intensity, normalise, cut_off_pixels)

        return radius, intensity


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    test_file = r'C:\Users\chem-hert4067\Documents\VEIRA\Analysis\C6D6\100 eV\Radial distributions\C3D3+&C6D6_2+_hansen-law_centre_182-5_166-5_mask_centre_178-5_152_radius_133_symmetrised.dat'
    r = np.loadtxt(test_file, delimiter='\t')

    plt.figure()
    plt.plot(r[:, 0], r[:, 1])

    test_fun = radial_dist_unit_conversion()
    r, i, u = test_fun(r[:, 0], r[:, 1], calibration='2k_rep_1.612k_ext_-50_MCPf_VEIRA_short_tube', cut_off_pixels=0,
                       type='momentum', mass=42)

    plt.figure()
    plt.plot(r, i)
    plt.xlabel(u)
    plt.show()
