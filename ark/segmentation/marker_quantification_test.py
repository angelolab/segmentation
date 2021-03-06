import numpy as np
import os
import pytest
import tempfile

import skimage.morphology as morph
from skimage.morphology import erosion

from ark.segmentation import marker_quantification
from ark.utils import test_utils

import ark.settings as settings


def test_compute_marker_counts_base():
    cell_mask, channel_data = test_utils.create_test_extraction_data()

    segmentation_labels = test_utils.make_labels_xarray(label_data=cell_mask,
                                                        compartment_names=['whole_cell'])

    input_images = test_utils.make_images_xarray(channel_data)

    # test utils output is 4D but tests require 3D
    segmentation_labels, input_images = segmentation_labels[0], input_images[0]

    segmentation_output = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels)

    # check that channel 0 counts are same as cell size
    assert np.array_equal(segmentation_output.loc['whole_cell', :, settings.CELL_SIZE].values,
                          segmentation_output.loc['whole_cell', :, 'chan0'].values)

    # check that channel 1 counts are 5x cell size
    assert np.array_equal(segmentation_output.loc['whole_cell', :, settings.CELL_SIZE].values * 5,
                          segmentation_output.loc['whole_cell', :, 'chan1'].values)

    # check that channel 2 counts are the same as channel 1
    assert np.array_equal(segmentation_output.loc['whole_cell', :, 'chan2'].values,
                          segmentation_output.loc['whole_cell', :, 'chan1'].values)

    # check that only cell1 is negative for channel 3
    assert segmentation_output.loc['whole_cell', 1, 'chan3'] == 0
    assert np.all(segmentation_output.loc['whole_cell', 2:, 'chan3'] > 0)

    # check that only cell2 is positive for channel 4
    assert segmentation_output.loc['whole_cell', 2, 'chan4'] > 0
    assert np.all(segmentation_output.loc['whole_cell', :1, 'chan4'] == 0)
    assert np.all(segmentation_output.loc['whole_cell', 3:, 'chan4'] == 0)

    # check that cell sizes are correct
    sizes = [np.sum(cell_mask == cell_id) for cell_id in [1, 2, 3, 5]]
    assert np.array_equal(sizes, segmentation_output.loc['whole_cell', :, settings.CELL_SIZE])

    # check that regionprops size matches with cell size
    assert np.array_equal(segmentation_output.loc['whole_cell', :, settings.CELL_SIZE],
                          segmentation_output.loc['whole_cell', :, 'area'])

    # test different extraction selection
    center_extraction = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels,
                                                    extraction='center_weighting')

    assert np.all(
        segmentation_output.loc['whole_cell', :, 'chan0'].values
        > center_extraction.loc['whole_cell', :, 'chan0'].values
    )


def test_compute_marker_counts_equal_masks():
    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # test whole_cell and nuclear compartments with same data
    segmentation_labels_equal = test_utils.make_labels_xarray(
        label_data=np.concatenate((cell_mask, cell_mask), axis=-1),
        compartment_names=['whole_cell', 'nuclear']
    )

    input_images = test_utils.make_images_xarray(channel_data)

    # test utils output is 4D but tests require 3D
    segmentation_labels_equal, input_images = segmentation_labels_equal[0], input_images[0]

    segmentation_output_equal = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels_equal,
                                                    nuclear_counts=True)

    assert np.all(segmentation_output_equal[0].values == segmentation_output_equal[1].values)


def test_compute_marker_counts_nuc_whole_cell_diff():
    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # nuclear mask is smaller
    nuc_mask = \
        np.expand_dims(erosion(cell_mask[0, :, :, 0], selem=morph.disk(1)), axis=0)
    nuc_mask = np.expand_dims(nuc_mask, axis=-1)

    unequal_masks = np.concatenate((cell_mask, nuc_mask), axis=-1)
    segmentation_labels_unequal = test_utils.make_labels_xarray(
        label_data=unequal_masks,
        compartment_names=['whole_cell', 'nuclear']
    )

    input_images = test_utils.make_images_xarray(channel_data)

    # test utils output is 4D but tests require 3D
    segmentation_labels_unequal, input_images = segmentation_labels_unequal[0], input_images[0]

    segmentation_output_unequal = \
        marker_quantification.compute_marker_counts(
            input_images=input_images,
            segmentation_labels=segmentation_labels_unequal,
            nuclear_counts=True)

    # make sure nuclear segmentations are smaller
    assert np.all(segmentation_output_unequal.loc['nuclear', :, 'cell_size'].values <
                  segmentation_output_unequal.loc['whole_cell', :, 'cell_size'].values)

    # check that channel 0 counts are same as cell size
    assert np.array_equal(segmentation_output_unequal.loc['nuclear', :, 'cell_size'].values,
                          segmentation_output_unequal.loc['nuclear', :, 'chan0'].values)

    # check that channel 1 counts are 5x cell size
    assert np.array_equal(segmentation_output_unequal.loc['nuclear', :, 'cell_size'].values * 5,
                          segmentation_output_unequal.loc['nuclear', :, 'chan1'].values)

    # check that channel 2 counts are the same as channel 1
    assert np.array_equal(segmentation_output_unequal.loc['nuclear', :, 'chan2'].values,
                          segmentation_output_unequal.loc['nuclear', :, 'chan1'].values)

    # check that only cell1 is negative for channel 3
    assert segmentation_output_unequal.loc['nuclear', 1, 'chan3'] == 0
    assert np.all(segmentation_output_unequal.loc['nuclear', 2:, 'chan3'] > 0)

    # check that only cell2 is positive for channel 4
    assert segmentation_output_unequal.loc['nuclear', 2, 'chan4'] > 0
    assert np.all(segmentation_output_unequal.loc['nuclear', :1, 'chan4'] == 0)
    assert np.all(segmentation_output_unequal.loc['nuclear', 3:, 'chan4'] == 0)

    # check that cell sizes are correct
    sizes = [np.sum(nuc_mask == cell_id) for cell_id in [1, 2, 3, 5]]
    assert np.array_equal(sizes, segmentation_output_unequal.loc['nuclear', :, 'cell_size'])

    assert np.array_equal(segmentation_output_unequal.loc['nuclear', :, 'cell_size'],
                          segmentation_output_unequal.loc['nuclear', :, 'area'])


def test_compute_marker_counts_no_coords():
    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # test whole_cell and nuclear compartments with same data
    segmentation_labels_equal = test_utils.make_labels_xarray(
        label_data=np.concatenate((cell_mask, cell_mask), axis=-1),
        compartment_names=['whole_cell', 'nuclear']
    )

    input_images = test_utils.make_images_xarray(channel_data)

    segmentation_labels_equal, input_images = segmentation_labels_equal[0], input_images[0]

    # different object properties can be supplied
    regionprops_features = ['label', 'area']
    excluded_defaults = ['eccentricity']

    segmentation_output_specified = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels_equal,
                                                    nuclear_counts=True,
                                                    regionprops_features=regionprops_features)

    assert np.all(np.isin(['label', 'area'], segmentation_output_specified.features.values))

    assert not np.any(np.isin(excluded_defaults, segmentation_output_specified.features.values))

    # these nuclei are all smaller than the cells, so we should get same result
    segmentation_output_specified_split = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels_equal,
                                                    nuclear_counts=True,
                                                    regionprops_features=regionprops_features,
                                                    split_large_nuclei=True)

    assert np.all(segmentation_output_specified_split == segmentation_output_specified)


def test_compute_marker_counts_no_labels():
    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # test whole_cell and nuclear compartments with same data
    segmentation_labels_equal = test_utils.make_labels_xarray(
        label_data=np.concatenate((cell_mask, cell_mask), axis=-1),
        compartment_names=['whole_cell', 'nuclear']
    )

    input_images = test_utils.make_images_xarray(channel_data)

    segmentation_labels_equal, input_images = segmentation_labels_equal[0], input_images[0]

    # different object properties can be supplied
    regionprops_features = ['coords', 'area']
    excluded_defaults = ['eccentricity']

    segmentation_output_specified = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels_equal,
                                                    nuclear_counts=True,
                                                    regionprops_features=regionprops_features)

    assert np.all(np.isin(['label', 'area'], segmentation_output_specified.features.values))

    assert not np.any(np.isin(excluded_defaults, segmentation_output_specified.features.values))

    # these nuclei are all smaller than the cells, so we should get same result
    segmentation_output_specified_split = \
        marker_quantification.compute_marker_counts(input_images=input_images,
                                                    segmentation_labels=segmentation_labels_equal,
                                                    nuclear_counts=True,
                                                    regionprops_features=regionprops_features,
                                                    split_large_nuclei=True)

    assert np.all(segmentation_output_specified_split == segmentation_output_specified)


def test_create_marker_count_matrices_base():

    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # generate data for two fovs offset
    cell_masks = np.zeros((2, 40, 40, 1), dtype="int16")
    cell_masks[0, :, :, 0] = cell_mask[0, :, :, 0]
    cell_masks[1, 5:, 5:, 0] = cell_mask[0, :-5, :-5, 0]

    tif_data = np.zeros((2, 40, 40, 5), dtype="int16")
    tif_data[0, :, :, :] = channel_data[0, :, :, :]
    tif_data[1, 5:, 5:, :] = channel_data[0, :-5, :-5, :]

    segmentation_labels = test_utils.make_labels_xarray(
        label_data=cell_masks,
        compartment_names=['whole_cell']
    )

    channel_data = test_utils.make_images_xarray(tif_data)

    normalized, _ = marker_quantification.create_marker_count_matrices(segmentation_labels,
                                                                       channel_data)

    assert normalized.shape[0] == 7

    assert np.array_equal(normalized['chan0'], np.repeat(1, len(normalized)))
    assert np.array_equal(normalized['chan1'], np.repeat(5, len(normalized)))

    # error checking
    with pytest.raises(ValueError):
        # attempt to pass non-xarray for segmentation_labels
        marker_quantification.create_marker_count_matrices(segmentation_labels.values,
                                                           channel_data)

    with pytest.raises(ValueError):
        marker_quantification.create_marker_count_matrices(segmentation_labels,
                                                           channel_data.values)

    segmentation_labels_bad = segmentation_labels.copy()
    segmentation_labels_bad = segmentation_labels_bad.reindex({'fovs': [1, 2]})

    with pytest.raises(ValueError):
        # attempt to pass segmentation_labels and channel_data with different fovs
        marker_quantification.create_marker_count_matrices(segmentation_labels_bad,
                                                           channel_data)


def test_create_marker_count_matrices_multiple_compartments():

    cell_mask, channel_data = test_utils.create_test_extraction_data()

    # generate data for two fovs offset
    cell_masks = np.zeros((2, 40, 40, 1), dtype="int16")
    cell_masks[0, :, :, 0] = cell_mask[0, :, :, 0]
    cell_masks[1, 5:, 5:, 0] = cell_mask[0, :-5, :-5, 0]

    channel_datas = np.zeros((2, 40, 40, 5), dtype="int16")
    channel_datas[0, :, :, :] = channel_data[0, :, :, :]
    channel_datas[1, 5:, 5:, :] = channel_data[0, :-5, :-5, :]

    # generate a second set of nuclear masks that are smaller than cell masks
    nuc_masks = np.zeros_like(cell_masks)
    nuc_masks[0, :, :, 0] = erosion(cell_masks[0, :, :, 0], selem=morph.disk(1))
    nuc_masks[1, :, :, 0] = erosion(cell_masks[1, :, :, 0], selem=morph.disk(1))

    # cell 2 in fov0 has no nucleus
    nuc_masks[0, nuc_masks[0, :, :, 0] == 2, 0] = 0

    # all of the nuclei have a label that is 2x the label of the corresponding cell
    nuc_masks *= 2

    unequal_masks = np.concatenate((cell_masks, nuc_masks), axis=-1)

    segmentation_labels_unequal = test_utils.make_labels_xarray(
        label_data=unequal_masks,
        compartment_names=['whole_cell', 'nuclear']
    )

    channel_data = test_utils.make_images_xarray(channel_datas)

    normalized, arcsinh = marker_quantification.create_marker_count_matrices(
        segmentation_labels_unequal,
        channel_data,
        nuclear_counts=True
    )

    # 7 total cells
    assert normalized.shape[0] == 7

    # channel 0 has a constant value of 1
    assert np.array_equal(normalized['chan0'], np.repeat(1, len(normalized)))

    # channel 1 has a constant value of 5
    assert np.array_equal(normalized['chan1'], np.repeat(5, len(normalized)))

    # these two channels should be equal for all cells
    assert np.array_equal(normalized['chan1'], normalized['chan2'])

    # check that cell with missing nucleus has size 0
    index = np.logical_and(normalized['label'] == 2, normalized['fov'] == 'fov0')
    assert normalized.loc[index, 'cell_size_nuclear'].values == 0

    # check that correct nuclear label is assigned to all cells
    normalized_with_nuc = normalized.loc[normalized['label'] != 2, ['label', 'label_nuclear']]
    assert np.array_equal(normalized_with_nuc['label'] * 2, normalized_with_nuc['label_nuclear'])


def test_generate_cell_data_tree_loading():
    # is_mibitiff False case, load from directory tree
    with tempfile.TemporaryDirectory() as temp_dir:
        # define 3 fovs and 3 imgs per fov
        fovs, chans = test_utils.gen_fov_chan_names(3, 3)

        tiff_dir = os.path.join(temp_dir, "single_channel_inputs")
        img_sub_folder = "TIFs"

        os.mkdir(tiff_dir)
        test_utils.create_paired_xarray_fovs(
            base_dir=tiff_dir,
            fov_names=fovs,
            channel_names=chans,
            img_shape=(40, 40),
            sub_dir=img_sub_folder,
            dtype="int16"
        )

        # define a subset of fovs
        fovs_subset = fovs[:2]

        # define a subset of fovs with file extensions
        fovs_subset_ext = fovs[:2]
        fovs_subset_ext[0] = str(fovs_subset_ext[0]) + ".tif"
        fovs_subset_ext[1] = str(fovs_subset_ext[1]) + ".tiff"

        # generate a sample segmentation_mask
        cell_mask, _ = test_utils.create_test_extraction_data()

        cell_masks = np.zeros((3, 40, 40, 1), dtype="int16")
        cell_masks[0, :, :, 0] = cell_mask[0, :, :, 0]
        cell_masks[1, 5:, 5:, 0] = cell_mask[0, :-5, :-5, 0]
        cell_masks[2, 10:, 10:, 0] = cell_mask[0, :-10, :-10, 0]

        segmentation_masks = test_utils.make_labels_xarray(
            label_data=cell_masks,
            compartment_names=['whole_cell']
        )

        with pytest.raises(ValueError):
            # specifying fovs not in the original segmentation mask
            marker_quantification.generate_cell_table(
                segmentation_labels=segmentation_masks.loc[["fov1"]], tiff_dir=tiff_dir,
                img_sub_folder=img_sub_folder, is_mibitiff=False, fovs=["fov1", "fov2"],
                batch_size=5)

        # generate sample norm and arcsinh data for all fovs
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=img_sub_folder, is_mibitiff=False, fovs=None, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0

        # generate sample norm and arcsinh data for a subset of fovs
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=img_sub_folder, is_mibitiff=False, fovs=fovs_subset, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0

        # generate sample norm and arcsinh data for a subset of fovs
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=img_sub_folder, is_mibitiff=False, fovs=fovs_subset_ext, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0


def test_generate_cell_data_mibitiff_loading():
    # is_mibitiff True case, load from mibitiff file structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # define 3 fovs and 2 mibitiff_imgs
        fovs, channels = test_utils.gen_fov_chan_names(3, 2)

        # define a subset of fovs
        fovs_subset = fovs[:2]

        # define a subset of fovs with file extensions
        fovs_subset_ext = fovs[:2]
        fovs_subset_ext[0] = str(fovs_subset_ext[0]) + ".tif"
        fovs_subset_ext[1] = str(fovs_subset_ext[1]) + ".tiff"

        tiff_dir = os.path.join(temp_dir, "mibitiff_inputs")

        os.mkdir(tiff_dir)
        test_utils.create_paired_xarray_fovs(
            base_dir=tiff_dir,
            fov_names=fovs,
            channel_names=channels,
            img_shape=(40, 40),
            mode='mibitiff',
            dtype=np.float32
        )

        # generate a sample segmentation_mask
        cell_mask, _ = test_utils.create_test_extraction_data()
        cell_masks = np.zeros((3, 40, 40, 1), dtype="int16")
        cell_masks[0, :, :, 0] = cell_mask[0, :, :, 0]
        cell_masks[1, 5:, 5:, 0] = cell_mask[0, :-5, :-5, 0]
        cell_masks[2, 10:, 10:, 0] = cell_mask[0, :-10, :-10, 0]
        segmentation_masks = test_utils.make_labels_xarray(
            label_data=cell_masks,
            compartment_names=['whole_cell']
        )

        # generate sample norm and arcsinh data for all fovs
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=tiff_dir, is_mibitiff=True, fovs=None, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0

        # generate sample norm and arcsinh data for a subset of fovs
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=tiff_dir, is_mibitiff=True, fovs=fovs_subset, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0

        # generate sample norm and arcsinh for a subset of fovs with file extensions
        norm_data, arcsinh_data = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=tiff_dir, is_mibitiff=True, fovs=fovs_subset_ext, batch_size=2)

        assert norm_data.shape[0] > 0 and norm_data.shape[1] > 0
        assert arcsinh_data.shape[0] > 0 and arcsinh_data.shape[1] > 0


def test_generate_cell_data_extractions():
    with tempfile.TemporaryDirectory() as temp_dir:
        # define 3 fovs and 3 imgs per fov
        fovs, chans = test_utils.gen_fov_chan_names(3, 3)

        tiff_dir = os.path.join(temp_dir, "single_channel_inputs")
        img_sub_folder = "TIFs"

        os.mkdir(tiff_dir)
        test_utils.create_paired_xarray_fovs(
            base_dir=tiff_dir,
            fov_names=fovs,
            channel_names=chans,
            img_shape=(40, 40),
            sub_dir=img_sub_folder,
            fills=True,
            dtype="int16"
        )

        # generate a sample segmentation_mask
        cell_mask, _ = test_utils.create_test_extraction_data()

        cell_masks = np.zeros((3, 40, 40, 1), dtype="int16")
        cell_masks[0, :, :, 0] = cell_mask[0, :, :, 0]
        cell_masks[1, 5:, 5:, 0] = cell_mask[0, :-5, :-5, 0]
        cell_masks[2, 10:, 10:, 0] = cell_mask[0, :-10, :-10, 0]

        segmentation_masks = test_utils.make_labels_xarray(
            label_data=cell_masks,
            compartment_names=['whole_cell']
        )

        default_norm_data, _ = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=img_sub_folder, is_mibitiff=False, batch_size=2,
        )

        # verify total intensity extraction
        assert np.all(
            default_norm_data.loc[default_norm_data[settings.CELL_LABEL] == 1][chans].values
            == np.arange(9).reshape(3, 3)
        )

        thresh_kwargs = {
            'threshold': 1
        }

        # verify thresh kwarg passes through
        positive_pixel_data, _ = marker_quantification.generate_cell_table(
            segmentation_labels=segmentation_masks, tiff_dir=tiff_dir,
            img_sub_folder=img_sub_folder, is_mibitiff=False, batch_size=2,
            extraction='positive_pixel', **thresh_kwargs
        )

        assert np.all(positive_pixel_data.iloc[:4][['chan0', 'chan1']].values == 0)
        assert np.all(positive_pixel_data.iloc[4:][chans].values == 1)
