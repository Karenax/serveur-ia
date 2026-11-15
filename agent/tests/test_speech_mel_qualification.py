"""Pure array boundaries of the isolated mel experiment; no model or audio."""
import numpy as np
import pytest

from scripts.qualify_speech_mel import short_mel


@pytest.mark.parametrize("frames", [2, 500, 2998, 3000])
def test_even_mel_keeps_all_frames_and_same_array(frames):
    features = np.arange(80 * frames, dtype=np.float32).reshape(80, frames)
    result = short_mel(features)
    assert result is features
    assert np.array_equal(result, features)


@pytest.mark.parametrize("frames", [1, 499, 2999])
def test_stride_two_adds_only_one_zero_without_losing_last_real_frame(frames):
    features = np.arange(80 * frames, dtype=np.float32).reshape(80, frames)
    result = short_mel(features)
    assert result.shape == (80, frames + 1)
    assert np.array_equal(result[:, :frames], features)
    assert np.array_equal(result[:, -1], np.zeros(80, dtype=np.float32))
    assert result.dtype == features.dtype


@pytest.mark.parametrize("frames", [0, 3001, 3200])
def test_empty_or_oversize_is_rejected_instead_of_truncating_audio(frames):
    with pytest.raises(ValueError):
        short_mel(np.zeros((80, frames), dtype=np.float32))


@pytest.mark.parametrize("shape,axis,length", [((500,), -1, 3000), ((1, 80, 500), -1, 3000),
    ((80, 500), 0, 3000), ((80, 500), -1, 500)])
def test_wrong_shape_axis_or_contract_cannot_change_preprocessing(shape, axis, length):
    with pytest.raises(ValueError):
        short_mel(np.zeros(shape, dtype=np.float32), length, axis=axis)
