import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit

from examples.utils.config import get_common_argument_parser, Config
from examples.utils.dataset_adapters import allen_dataset
from pyspikelib.fit_predict import tsfresh_fit_predict

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def get_argument_parser():
    default_config = {
        'seed': 0,
        'window': 50,
        'step': 20,
        'trials': 10,
        'scale': True,
        'remove_low_variance': True,
        'train_subsample_factor': 0.7,
        'test_subsample_factor': 0.7,
        'delimiter': ',',
        'feature_set': None,
        'dataset': './data/allen',
        'n_trees': 200,
    }
    parser = get_common_argument_parser(default_config)
    parser.add_argument('--n-trees', default=default_config['n_trees'], type=int)
    return parser


def main(argv):
    parser = get_argument_parser()
    args = parser.parse_args(args=argv)
    config = Config()
    config.update_from_args(args, parser)

    np.random.seed(config.seed)

    vip_datapath = Path(config.dataset) / 'Vip_spikes_dict_new.pkl'
    vip_spike_data = allen_dataset(vip_datapath)
    sst_datapath = Path(config.dataset) / 'Sst_spikes_dict_new.pkl'
    sst_spike_data = allen_dataset(sst_datapath)

    group_split = GroupShuffleSplit(n_splits=1, test_size=0.5)
    X = np.hstack([vip_spike_data.series.values, sst_spike_data.series.values])
    y = np.hstack(
        [np.ones(vip_spike_data.shape[0]), np.zeros(sst_spike_data.shape[0])]
    )
    groups = np.hstack([vip_spike_data.groups.values, sst_spike_data.groups.values])

    for train_index, test_index in group_split.split(X, y, groups):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]

    X_train = pd.DataFrame({'series': X_train, 'groups': groups[train_index]})
    X_test = pd.DataFrame({'series': X_test, 'groups': groups[test_index]})

    forest = RandomForestClassifier(
        n_estimators=config.n_trees, random_state=config.seed, n_jobs=-1
    )
    scores = tsfresh_fit_predict(forest, X_train, X_test, y_train, y_test, config)
    return scores


if __name__ == '__main__':
    main(sys.argv[1:])
