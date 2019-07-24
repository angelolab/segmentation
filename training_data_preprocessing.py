# preprocess label masks from hand contoured cells to generate training data

import skimage.io as io
import helper_functions
import importlib
importlib.reload(helper_functions)

base_dir = '/Users/noahgreenwald/Documents/Grad_School/Lab/Segmentation_Project/Contours/First_Run/Point23/'
base_dir = '/Users/noahgreenwald/Google Drive/Grad School/Lab/Segmentation_Contours/Practice_Run_Zips/'

total_cell = io.imread(base_dir + 'Nuclear_Interior_Border_Mask.tif')
interior_cell = io.imread(base_dir + 'Nuclear_Interior_Mask.tif')
mask = helper_functions.process_training_data(interior_cell, total_cell)
io.imshow(mask)

io.imsave(base_dir + 'Nuclear_Mask_Label.tif', mask)