import os

import numpy as np
import pandas as pd


def decay_function(param, t, num_iters):
    """Decays the parameter using an asymptotic decay function

    Args:
        param (float):
            The value to decay (either sigma or learning_rate)
        t (int):
            The current iteration index
        num_iters (int):
            The maximum number of iterations

    Returns:
        float:
            The decayed parameter
    """

    return param / (1 + t / (num_iters / 2))


def winner(sample, weights):
    """Find the coordinates to the winning neuron in the SOM

    Args:
        sample (numpy.ndarray):
            A row in the pixel matrix identifying information associated with one pixel
        weights (numpy.ndarray):
            A weight matrix of dimensions [num_x, num_y, num_chans]

    Returns:
        tuple:
            The coordinates of the winning neuron
    """

    # get euclidean distance between the sample and the weights
    activation_map = np.linalg.norm(np.subtract(sample, weights), axis=-1)

    # find the winning neuron's coordinates, needed for easy access
    winning_coords = np.unravel_index(activation_map.argmin(), activation_map.shape)

    return winning_coords


def update(sample, weights, winning_coords, sigma, learning_rate, x_mesh, y_mesh):
    """Updates the weights, learning rate, and sigma parameters

    Args:
        sample (numpy.ndarray):
            A row in the pixel matrix identifying information associated with one pixel
        weights (numpy.ndarray):
            A weight matrix of dimensions [num_x, num_y, num_chans]
        winning_coords (tuple):
            A coordinate array which indicates the winning neuron's position
        sigma (float):
            Determines the spread of the Gaussian neighborhood function, decayed
        learning_rate (float):
            Determines how sensitive the weight updates will be to new data, decayed
        x_mesh (numpy.ndarray):
            The x coordinate matrix of the weights vectors
        y_mesh (numpy.ndarray):
            The y coordinate matrix of the weights vectors

    Returns:
        numpy.ndarray:
            The updated weights matrix
    """

    # return a Gaussian centered around the winning coordinates
    d = 2 * np.pi * sigma * sigma
    ax = np.exp(-np.power(x_mesh - x_mesh.T[winning_coords], 2) / d)
    ay = np.exp(-np.power(y_mesh - y_mesh.T[winning_coords], 2) / d)
    g = (ax * ay).T * learning_rate

    # update the weights based on the Gaussian neighborhood
    new_weights = weights + np.einsum('ij, ijk->ijk', g, sample - weights)

    return new_weights


def train_som(pixel_mat, x_neurons, y_neurons, num_passes,
              sigma=1.0, learning_rate=0.5, random_seed=None):
    """Trains the SOM by iterating through the each data point and updating the params

    Args:
        pixel_mat (pandas.DataFrame):
            A matrix with pixel-level channel information for non-zero pixels in img_xr
        x_neurons (int):
            The number of x neurons to use
        y_neurons (int):
            The number of y neurons to use
        num_passes (int):
            The maximum number of passes to make through the dataset for training
        sigma (float):
            Determines the spread of the Gaussian neighborhood function
        learning_rate (float):
            Determines how sensitive the weight updates will be to new data
        random_seed (int):
            The seed to set for random weight initialization

    Returns:
        numpy.ndarray:
            The weights matrix after training
    """

    # define the random generator
    rand_gen = np.random.RandomState(random_seed)

    # initialize the weights and normalize
    weights = rand_gen.rand(x_neurons, y_neurons, pixel_mat.shape[1]) * 2 - 1
    weights /= np.linalg.norm(weights, axis=-1, keepdims=True)

    # define meshgrid coords for the weights matrix, convert to float (yikes, memory...)
    x_mesh, y_mesh = np.meshgrid(np.arange(x_neurons), np.arange(y_neurons))
    x_mesh = x_mesh.astype(float)
    y_mesh = y_mesh.astype(float)

    # define the number of iterations and the row in pixel_mat corresponding to each iteration
    num_iters = num_passes * pixel_mat.shape[0]
    iter_row = np.arange(num_iters) % pixel_mat.shape[0]

    for t, row in enumerate(iter_row):
        # find the winning neuron's coordinates
        winning_coords = winner(pixel_mat.loc[row, :].values, weights)

        # decay both sigma and learning_rate using the decay function
        decay_sigma = decay_function(sigma, t, num_iters)
        decay_learning_rate = decay_function(learning_rate, t, num_iters)

        # update the weights
        weights = update(pixel_mat.loc[row, :].values, weights,
                         winning_coords, decay_sigma, decay_learning_rate,
                         x_mesh, y_mesh)

    return weights


def cluster_som(pixel_mat, weights):
    """Assigns the cluster label to each entry in the pixel matrix based on the trained weights

    Args:
        pixel_mat (pandas.DataFrame):
            A matrix with pixel-level channel information for non-zero pixels in img_xr
        weights (numpy.ndarray):
            The weights matrix after training

    Returns:
        pandas.Series:
            The cluster labels to assign to the corresponding rows in pixel_mat
    """

    # extract the coordinate associated with the winning neuron for each row
    cluster_coords = pixel_mat.apply(
        lambda row: winner(np.array(list(row.values)), weights), axis=1).astype(str)

    # reassign the coordinates to integers to make the label col more understandable
    unique_cluster_coords = cluster_coords.unique()
    coord_to_label = list(range(len(unique_cluster_coords)))
    cluster_labels = cluster_coords.replace(to_replace=unique_cluster_coords,
                                            value=coord_to_label)

    return cluster_labels