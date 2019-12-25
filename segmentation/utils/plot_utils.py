import numpy as np
import os
import copy


from skimage.segmentation import find_boundaries
import matplotlib.pyplot as plt
import matplotlib as mpl


# plotting functions

def plot_overlay(predicted_contour, plotting_tif=None, alternate_contour=None, path=None):
    """Take in labeled contour data, along with optional mibi tif and second contour, and overlay them for comparison"

    Args:
        predicted_contour: 2D numpy array of labeled cell objects
        plotting_tif: 2D numpy array of imaging signal
        alternate_contour: 2D numpy array of labeled cell objects
        path: path to save the resulting image

    outputs:
        plot viewer: plots the outline(s) of the mask(s) as well as intensity from plotting tif
            predicted_contour in red
            alternate_contour in white
        overlay: saves as TIF in file path if specified
    """

    if plotting_tif.shape != predicted_contour.shape:
        raise ValueError("plotting_tif and predicted_contour array dimensions not equal.")

    if len(np.unique(predicted_contour)) < 2:
        raise ValueError("predicted contour is not labeled")

    if path is not None:
        if os.path.exists(os.path.split(path)[0]) is False:
            raise ValueError("File path does not exist.")

    # define borders of cells in mask
    predicted_contour_mask = find_boundaries(predicted_contour, connectivity=1, mode='inner').astype(np.uint8)

    # creates transparent mask for easier visualization of TIF data
    rgb_mask = np.ma.masked_where(predicted_contour_mask == 0, predicted_contour_mask)

    if alternate_contour is not None:

        if predicted_contour.shape != alternate_contour.shape:
            raise ValueError("predicted_contour and alternate_contour array dimensions not equal.")

        # define borders of cell in mask
        alternate_contour_mask = find_boundaries(alternate_contour, connectivity=1, mode='inner').astype(np.uint8)

        # creates transparent mask for easier visualization of TIF data
        rgb_mask_2 = np.ma.masked_where(alternate_contour_mask == 0, predicted_contour_mask)

        # creates plots overlaying ground truth and predicted contour masks
        overlay = plt.figure()
        plt.imshow(plotting_tif, clim=(0, 15))
        plt.imshow(rgb_mask_2, cmap="Greys", interpolation='none')
        plt.imshow(rgb_mask, cmap='autumn', interpolation='none')

        if path is not None:
            overlay.savefig(os.path.join(path), dpi=800)
            plt.close(overlay)

    else:
        # if only one mask provided
        overlay = plt.figure()
        plt.imshow(plotting_tif, clim=(0, 15))
        plt.imshow(rgb_mask, cmap='autumn', interpolation='none')

        if path is not None:
            overlay.savefig(os.path.join(path), dpi=800)
            plt.close(overlay)


def randomize_labels(label_map):
    """Takes in a labeled matrix and swaps the integers around so that color gradient has better contrast

    Inputs:
    label_map(2D numpy array): labeled TIF with each object assigned a unique value

    Outputs:
    swapped_map(2D numpy array): labeled TIF with object labels permuted"""

    max_val = np.max(label_map)
    for cell_target in range(1, max_val):
        swap_1 = cell_target
        swap_2 = np.random.randint(1, max_val)
        swap_1_mask = label_map == swap_1
        swap_2_mask = label_map == swap_2
        label_map[swap_1_mask] = swap_2
        label_map[swap_2_mask] = swap_1

    label_map = label_map.astype('int16')

    return label_map


def outline_objects(L_matrix, list_of_lists):
    """takes in an L matrix generated by skimage.label, along with a list of lists, and returns a mask that has the
    pixels for all cells from each list represented as integer values for easy plotting"""

    L_plot = copy.deepcopy(L_matrix).astype(float)

    for idx, val in enumerate(list_of_lists):
        mask = np.isin(L_plot, val)

        # use a negative value to not interfere with cell labels
        L_plot[mask] = -(idx + 2)

    L_plot[L_plot > 1] = 1
    L_plot = np.absolute(L_plot)
    L_plot = L_plot.astype('int16')
    return L_plot


def plot_color_map(outline_matrix, names,
                   plotting_colors=['Black', 'Grey', 'Blue', 'Green', 'Pink', 'moccasin', 'tan', 'sienna', 'firebrick'],
                   ground_truth=None, save_path=None):
    """Plot label map with cells of specified category colored the same

        Args
            outline_matrix: output of outline_objects function which assigns same value to cells of same class
            names: list of names for each category to use for plotting
            plotting_colors: list of colors to use for plotting cell categories
            ground truth: optional argument to supply label map of true segmentation to be plotted alongside
            save_path: optional argument to save plot as TIF

        Returns
            Displays plot in window"""

    num_categories = np.max(outline_matrix)
    plotting_colors = plotting_colors[:num_categories + 1]
    cmap = mpl.colors.ListedColormap(plotting_colors)

    if ground_truth is not None:
        fig, ax = plt.subplots(nrows=1, ncols=2)
        mat = ax[0].imshow(outline_matrix, cmap=cmap, vmin=np.min(outline_matrix) - .5,
                           vmax=np.max(outline_matrix) + .5)
        swapped = randomize_labels(ground_truth)
        ax[1].imshow(swapped)
    else:
        fig, ax = plt.subplots(nrows=1, ncols=1)
        mat = ax.imshow(outline_matrix, cmap=cmap, vmin=np.min(outline_matrix) - .5,
                           vmax=np.max(outline_matrix) + .5)

    # tell the colorbar to tick at integers
    cbar = fig.colorbar(mat, ticks=np.arange(np.min(outline_matrix), np.max(outline_matrix) + 1))

    cbar.ax.set_yticklabels(names)


    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, dpi=200)


def plot_barchart_errors(pd_array, contour_errors, predicted_errors, save_path=None):

    """Plot different error types in a barchart, along with cell-size correlation in a scatter plot
        Args
            pd_array: pandas cell array representing error types for each class of cell
            cell_category: list of error types to extract from array
            save_path: optional file path to save generated TIF

        Returns
            Display plot on viewer"""

    # make sure all supplied categories are column names
    if np.any(~np.isin(contour_errors + predicted_errors, pd_array.columns)):
        raise ValueError("Invalid column name")

    fig, ax = plt.subplots(2, 1, figsize=(10, 10))

    ax[0].scatter(pd_array["contour_cell_size"], pd_array["predicted_cell_size"])
    ax[0].set_xlabel("Contoured Cell")
    ax[0].set_ylabel("Predicted Cell")

    # compute percentage of different error types
    errors = np.zeros(len(predicted_errors) + len(contour_errors))
    for i in range(len(contour_errors)):
        errors[i] = len(set(pd_array.loc[pd_array[contour_errors[i]], "contour_cell"]))

    for i in range(len(predicted_errors)):
        errors[i + len(contour_errors)] = len(set(pd_array.loc[pd_array[predicted_errors[i]], "predicted_cell"]))

    errors = errors / len(set(pd_array["predicted_cell"]))
    position = range(len(errors))
    ax[1].bar(position, errors)

    ax[1].set_xticks(position)
    ax[1].set_xticklabels(contour_errors + predicted_errors)
    ax[1].set_title("Fraction of cells misclassified")

    if save_path is not None:
        fig.savefig(save_path, dpi=200)

def plot_barchart(values, labels, title, save_path=None):
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    position = range(len(values))
    ax.bar(position, values)
    ax.set_xticks(position)
    ax.set_xticklabels(labels)
    ax.set_title(title)

    if save_path is not None:
        fig.savefig(save_path, dpi=200)