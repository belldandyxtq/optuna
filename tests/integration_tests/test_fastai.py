from functools import partial
from typing import Any
from typing import Tuple

import fastai.basic_data
from fastai.basic_data import DataBunch
from fastai.basic_train import Learner
from fastai.metrics import accuracy
import numpy as np
import pytest
import torch.nn as nn
import torch.utils.data
from torch.utils.data import Dataset

import optuna
from optuna.integration import FastAIPruningCallback
from optuna.testing.integration import DeterministicPruner


# See https://docs.fast.ai/basic_data.html#Using-a-custom-Dataset-in-fastai.
class ArrayDataset(Dataset):
    "Sample numpy array dataset"

    def __init__(self, x: Any, y: Any) -> None:

        self.x, self.y = x, y
        self.c = 2

    def __len__(self) -> int:

        return len(self.x)

    def __getitem__(self, i: int) -> Tuple[Any, Any]:

        return self.x[i], self.y[i]


@pytest.fixture(scope="session")
def tmpdir(tmpdir_factory: Any) -> Any:

    return tmpdir_factory.mktemp("fastai_integration_test")


def test_fastai_pruning_callback(tmpdir: Any) -> None:

    train_x = np.zeros((16, 20), np.float32)
    train_y = np.zeros((16,), np.int64)
    valid_x = np.zeros((4, 20), np.float32)
    valid_y = np.zeros((4,), np.int64)
    train_ds = ArrayDataset(train_x, train_y)
    valid_ds = ArrayDataset(valid_x, valid_y)

    data_bunch = DataBunch.create(
        train_ds=train_ds, valid_ds=valid_ds, test_ds=None, path=tmpdir, bs=1  # batch size
    )

    def objective(trial: optuna.trial.Trial) -> float:

        model = nn.Sequential(nn.Linear(20, 1), nn.Sigmoid())
        learn = Learner(
            data_bunch,
            model,
            metrics=[accuracy],
            callback_fns=[partial(FastAIPruningCallback, trial=trial, monitor="valid_loss")],
        )

        learn.fit(1)

        return 1.0

    study = optuna.create_study(pruner=DeterministicPruner(True))
    study.optimize(objective, n_trials=1)
    assert study.trials[0].state == optuna.trial.TrialState.PRUNED

    study = optuna.create_study(pruner=DeterministicPruner(False))
    study.optimize(objective, n_trials=1)
    assert study.trials[0].state == optuna.trial.TrialState.COMPLETE
    assert study.trials[0].value == 1.0


# https://github.com/optuna/optuna/pull/1399#issuecomment-646956305
torch.utils.data.DataLoader.__init__ = fastai.basic_data.old_dl_init
