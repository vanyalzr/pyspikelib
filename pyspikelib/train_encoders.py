# PySpikeLib: A set of tools for neuronal spiking data mining
# Copyright (c) 2020 Ivan Lazarevich.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import numpy as np

from functools import partial
from sklearn.base import TransformerMixin

from pyspikelib.base_transformers import NoFitMixin


class SpikeTrainTransform(TransformerMixin, NoFitMixin):
    """Base class for spike train transforms"""

    def __init__(self):
        super().__init__()

    @staticmethod
    def string_to_float_series(string_series, delimiter=None):
        return np.array([float(value) for value in string_series.split(delimiter)])

    def numpy_transform(self, tensor, axis):
        raise NotImplementedError

    def single_train_transform(self, tensor):
        raise NotImplementedError

    def transform(self, X, y=None, format='numpy', axis=-1, delimiter=None):
        if format == 'numpy':
            X = self.numpy_transform(X, axis)
            return X
        join_delimiter = ' ' if delimiter is None else delimiter
        for train_index, spike_train in enumerate(X.series.values):
            train = self.string_to_float_series(spike_train, delimiter=delimiter)
            transfomed_train = self.single_train_transform(train)
            transfomed_series = join_delimiter.join(
                ['{:.2f}'.format(value) for value in transfomed_train]
            )
            X.series.iloc[train_index] = transfomed_series
        return X


class ISIShuffleTransform(SpikeTrainTransform):
    """Randomly permute ISIs in each spike train in-place"""

    def __init__(self):
        super().__init__()

    @staticmethod
    def shuffle_along_axis(tensor, axis):
        b = tensor.swapaxes(axis, -1)
        shp = b.shape[:-1]
        for ndx in np.ndindex(shp):
            np.random.shuffle(b[ndx])

    def numpy_transform(self, tensor, axis=-1):
        self.shuffle_along_axis(tensor, axis)
        return tensor

    def single_train_transform(self, tensor):
        np.random.shuffle(tensor)
        return tensor


class TrainBinarizationTransform(SpikeTrainTransform):
    """Turn an ISI series into a sequence of time bins with spike occurences"""

    def __init__(
        self, bin_size, keep_spike_counts=True, train_duration=None, start_time=None
    ):
        super().__init__()
        self.bin_size = bin_size
        self.keep_counts = keep_spike_counts
        self.train_duration = train_duration
        self.start_time = start_time
        self.fixed_size_output = (
            self.start_time is not None and self.train_duration is not None
        )

    def numpy_transform(self, tensor, axis=1):
        if self.fixed_size_output:
            return np.apply_along_axis(
                partial(self.single_train_transform, axis=axis), axis, tensor
            )
        else:
            single_train_transform = partial(self.single_train_transform, axis=axis)
            variable_length_transform = lambda series: list(
                single_train_transform(series)
            )
            return np.apply_along_axis(variable_length_transform, axis, tensor)

    def single_train_transform(self, series, axis):
        spike_times = np.cumsum(series, axis)
        start_time = spike_times.min() if self.start_time is None else self.start_time
        duration = (
            spike_times.max()
            if self.train_duration is None
            else self.train_duration + start_time
        )
        binarized_spike_train = np.histogram(
            spike_times,
            bins=int(duration / self.bin_size),
            range=(start_time, duration),
        )[0].astype(np.float32)
        if not self.keep_counts:
            binarized_spike_train = (binarized_spike_train > 0).astype(np.float32)
        return binarized_spike_train


class SpikeTimesToISITransform(SpikeTrainTransform):
    def __init__(self):
        super().__init__()

    def numpy_transform(self, tensor, axis=1):
        return np.diff(tensor, axis=axis)

    def single_train_transform(self, tensor):
        return np.diff(tensor)


# ToDo: jitter, rate estimation ...
