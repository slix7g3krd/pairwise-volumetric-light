import pytest
from render import volumetric_light as mod

CASES = [
    ("step", 'm.step_size(10.0, 2) == approx(5.0)'),
    ("bilateral", 'm.bilateral_weight(1.0, 2.0) == approx(0.5)'),
    ("trans_zero", 'm.transmittance(0.0, 1.0) == approx(1.0)'),
    ("trans_one", 'm.transmittance(1.0, 1.0) == approx(0.3679, rel=1e-3)'),
    ("phase_iso", 'm.phase_weight(0.0, 0.0) == approx(1.0)'),
    ("phase_fwd", 'm.phase_weight(1.0, 0.5) == approx(1.5)'),
    ("early_true", 'm.early_exit(1.0, 2.0, 1.5) is True'),
    ("early_false", 'm.early_exit(1.0, 4.0, 1.5) is False'),
    ("history_half", 'm.history_decay(2.0, 4.0) == approx(0.5)'),
    ("spot_inner", 'm.spot_attenuation(0.0, 10.0, 20.0) == approx(1.0)'),
    ("spot_outer", 'm.spot_attenuation(25.0, 10.0, 20.0) == approx(0.0)'),
    ("encode", 'm.encode_after_light(1.0, 2.0) == approx(2.0)'),
    ("async", 'm.async_lag(3, 5) == 2'),
    ("view", 'm.view_scale(1920, 960) == 2'),
    ("trans_dense", 'm.transmittance(2.0, 1.0) == approx(0.1353, rel=1e-3)')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
