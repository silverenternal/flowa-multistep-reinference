"""Guard against pooled records, missing seeds and mixed checkpoints."""

import pytest

from tools.review_mnist_sensitivity_20261103 import aggregate


def fixture_rows():
    return [
        dict(
            axis="beta",
            beta_total=0.3,
            rounds=4,
            steps=50,
            arm="test",
            seed_label=s,
            protocol="same",
            baseline=10.0,
            framework=10.0 + i,
            source=f"seed{s}",
        )
        for i, s in zip([-1.0, 0.0, 1.0], [42, 43, 44], strict=True)
    ]


def test_three_seed_interval_not_record_interval():
    row = aggregate(fixture_rows())[0]
    assert row["delta"] == 0
    assert row["velocity_calls"] == 200
    assert row["ci95_seed_t"] == pytest.approx([-2.4841377117, 2.4841377117])


@pytest.mark.parametrize("defect", ["missing", "duplicate", "protocol", "nonfinite"])
def test_bad_group_rejected(defect):
    rows = fixture_rows()
    if defect == "missing":
        rows.pop()
    elif defect == "duplicate":
        rows[-1]["seed_label"] = 42
    elif defect == "protocol":
        rows[-1]["protocol"] = "other"
    else:
        rows[-1]["framework"] = float("nan")
    with pytest.raises(ValueError):
        aggregate(rows)
