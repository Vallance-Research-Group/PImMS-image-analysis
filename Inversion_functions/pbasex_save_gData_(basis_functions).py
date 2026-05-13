import numpy as np
import time
import os
try:
    from gData import get_gData
except ModuleNotFoundError:
    from Inversion_functions.gData import get_gData

def main():
    # Settings
    save_path = None # Automatic file naming if none
    save_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Basis_sets') # Directory to save the data
    nx = 200  # nx x nx quadrant
    xkratio = 1 # Ratio of radial basis functions to pixel radii
    lmax = 4 # Up to l=28
    k_spacing = 'linear' # Even pixel or energy bins
    gData = {}
    gData['rBF'] = 'gauss' # Gaussian basis function

    # Set up the parameters
    gData['x'] = np.arange(nx, dtype='double')

    if k_spacing=='linear':

    	gData['k'] = np.arange(0, nx, xkratio) + 0.5 * (xkratio - 1)
    	gData['params'] = 0.7 * xkratio # Gaussian width

    elif k_spacing=='quadratic':

    	gData['k'] = np.sqrt(np.linspace(0, (nx-1)**2, nx))
    	gData['params'] = xkratio

    gData['l'] =  2 * np.arange(lmax/2 + 1).astype(int)

    if gData['rBF'] == 'custom':

    	def rBF(r, k, params):

    		return 1/((x-k)**2+(params/2)**2) # Lorentzian basis function

    	def zIP(r, k, params):

    		return np.sqrt((np.sqrt(max(0, 10-(params/2)**2)) + k)**2 - r**2)

    	trapz_step = 0.1

    	custom_rBF = (rBF, zIP, trapz_step)

    else:

    	custom_rBF = None

    np.seterr("ignore")

    t0 = time.time()
    get_gData(gData, save_path=save_path, save_dir=save_dir, custom_rBF=custom_rBF)
    print(time.time()-t0)

if __name__ == '__main__':
    main()
