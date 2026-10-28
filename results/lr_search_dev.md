| model   | layer     |    lr |    seed |   best_epoch |   epochs_run |   dev_exact_p |   dev_exact_r |   dev_exact_f1 |   dev_partial_f1 |   seconds | device                  |
|:--------|:----------|------:|--------:|-------------:|-------------:|--------------:|--------------:|---------------:|-----------------:|----------:|:------------------------|
| bert    | knowledge | 2e-05 | 3477689 |            2 |            5 |        0.5547 |        0.5801 |         0.5671 |           0.7854 |     114.3 | NVIDIA GeForce RTX 4090 |
| bert    | knowledge | 3e-05 | 3477689 |            7 |           10 |        0.5839 |        0.6304 |         0.6062 |           0.8023 |     202.5 | NVIDIA GeForce RTX 4090 |
| bert    | knowledge | 5e-05 | 3477689 |           10 |           10 |        0.5612 |        0.6542 |         0.6041 |           0.7839 |     215.2 | NVIDIA GeForce RTX 4090 |
| jobbert | knowledge | 2e-05 | 3477689 |           10 |           10 |        0.5616 |        0.6752 |         0.6132 |           0.7871 |     195.3 | NVIDIA GeForce RTX 4090 |
| jobbert | knowledge | 3e-05 | 3477689 |           10 |           10 |        0.5744 |        0.678  |         0.6219 |           0.7948 |     206.5 | NVIDIA GeForce RTX 4090 |
| jobbert | knowledge | 5e-05 | 3477689 |           10 |           10 |        0.58   |        0.6999 |         0.6343 |           0.7976 |     222.7 | NVIDIA GeForce RTX 4090 |
| bert    | skill     | 2e-05 | 3477689 |            8 |           10 |        0.4803 |        0.5355 |         0.5064 |           0.7854 |     209.3 | NVIDIA GeForce RTX 4090 |
| bert    | skill     | 3e-05 | 3477689 |           10 |           10 |        0.5078 |        0.5449 |         0.5257 |           0.7987 |     213.3 | NVIDIA GeForce RTX 4090 |
| bert    | skill     | 5e-05 | 3477689 |            8 |           10 |        0.4888 |        0.571  |         0.5267 |           0.7783 |     213.4 | NVIDIA GeForce RTX 4090 |
| jobbert | skill     | 2e-05 | 3477689 |            9 |           10 |        0.5057 |        0.5757 |         0.5385 |           0.8072 |     211.5 | NVIDIA GeForce RTX 4090 |
| jobbert | skill     | 3e-05 | 3477689 |            8 |           10 |        0.5225 |        0.5636 |         0.5423 |           0.7983 |     196.9 | NVIDIA GeForce RTX 4090 |
| jobbert | skill     | 5e-05 | 3477689 |           10 |           10 |        0.5341 |        0.5785 |         0.5554 |           0.8096 |     211.6 | NVIDIA GeForce RTX 4090 |