# This file includes routines for basic signal processing including framing and computing power spectra.
# Author: James Lyons 2012
import numpy
import math
import time
import decimal
import logging
# from numba import jit
# from numba import njit


def round_half_up(number):
    return int(decimal.Decimal(number).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP))


# @njit
def rolling_window(a, window, step=1):
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return numpy.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)[::step]


def framesig(sig, frame_len, frame_step, dither=1.0, preemph=0.97, remove_dc_offset=True, wintype='hamming', stride_trick=True):
    """Frame a signal into overlapping frames.

    :param sig: the audio signal to frame.
    :param frame_len: length of each frame measured in samples.
    :param frame_step: number of samples after the start of the previous frame that the next frame should begin.
    :param winfunc: the analysis window to apply to each frame. By default no window is applied.
    :param stride_trick: use stride trick to compute the rolling window and window multiplication faster
    :returns: an array of frames. Size is NUMFRAMES by frame_len.
    """
    slen = len(sig)
    # frame_len = int(round_half_up(frame_len))
    # frame_step = int(round_half_up(frame_step))
    frame_len = 400
    frame_step = 160

    if slen <= frame_len:
        numframes = 1
    else:
        numframes = 1 + ((slen - frame_len) // frame_step)

    # check kaldi/src/feat/feature-window.h
    padsignal = sig[:(numframes-1)*frame_step+frame_len]

    win = numpy.empty(frame_len)
    for i in range(frame_len):
        win[i] = (0.5-0.5*numpy.cos(2*numpy.pi/(frame_len-1)*i))**0.85

    if stride_trick:
        frames = rolling_window(padsignal, window=frame_len, step=frame_step)
    else:
        indices = numpy.tile(numpy.arange(0, frame_len), (numframes, 1)) + numpy.tile(
            numpy.arange(0, numframes * frame_step, frame_step), (frame_len, 1)).T
        indices = numpy.array(indices, dtype=numpy.int32)
        frames = padsignal[indices]
        win = numpy.tile(win, (numframes, 1))

    frames = frames.astype(numpy.float32)
    # for frm in range(frames.shape[0]): #随机噪声处理，推理去掉
        # frames[frm, :] = do_dither(frames[frm, :], dither)        # dither
        # frames[frm, :] = do_remove_dc_offset(frames[frm, :])      # remove dc offset
        # frames[frm, :] =do_preemphasis(frames[frm, :], preemph)    # preemphasize
    return frames * win


def magspec(frames, NFFT):
    """Compute the magnitude spectrum of each frame in frames. If frames is an NxD matrix, output will be Nx(NFFT/2+1).

    :param frames: the array of frames. Each row is a frame.
    :param NFFT: the FFT length to use. If NFFT > frame_len, the frames are zero-padded.
    :returns: If frames is an NxD matrix, output will be Nx(NFFT/2+1). Each row will be the magnitude spectrum of the corresponding frame.
    """
    # if numpy.shape(frames)[1] > NFFT:
    #     logging.warn(
    #         'frame length (%d) is greater than FFT size (%d), frame will be truncated. Increase NFFT to avoid.', numpy.shape(frames)[1], NFFT)
    complex_spec = numpy.fft.rfft(frames, NFFT)
    return numpy.absolute(complex_spec)


def powspec(frames, NFFT):
    """Compute the power spectrum of each frame in frames. If frames is an NxD matrix, output will be Nx(NFFT/2+1).

    :param frames: the array of frames. Each row is a frame.
    :param NFFT: the FFT length to use. If NFFT > frame_len, the frames are zero-padded.
    :returns: If frames is an NxD matrix, output will be Nx(NFFT/2+1). Each row will be the power spectrum of the corresponding frame.
    """
    return numpy.square(magspec(frames, NFFT))


# @njit
def logpowspec(frames, NFFT, norm=1):
    """Compute the log power spectrum of each frame in frames. If frames is an NxD matrix, output will be Nx(NFFT/2+1).

    :param frames: the array of frames. Each row is a frame.
    :param NFFT: the FFT length to use. If NFFT > frame_len, the frames are zero-padded.
    :param norm: If norm=1, the log power spectrum is normalised so that the max value (across all frames) is 0.
    :returns: If frames is an NxD matrix, output will be Nx(NFFT/2+1). Each row will be the log power spectrum of the corresponding frame.
    """
    ps = powspec(frames, NFFT)
    ps[ps <= 1e-30] = 1e-30
    lps = 10 * numpy.log10(ps)
    if norm:
        return lps - numpy.max(lps)
    else:
        return lps


def do_dither(signal, dither_value=1.0):
    signal += numpy.random.normal(size=signal.shape) * dither_value
    return signal


# @njit
def do_remove_dc_offset(signal):
    signal -= numpy.mean(signal)
    return signal


# @njit
def do_preemphasis(signal, coeff=0.97):
    """perform preemphasis on the input signal.

    :param signal: The signal to filter.
    :param coeff: The preemphasis coefficient. 0 is no filter, default is 0.95.
    :returns: the filtered signal.
    """
    return numpy.append((1-coeff)*signal[0], signal[1:] - coeff * signal[:-1])
    # signal[1:]=signal[1:] - coeff * signal[:-1]
    # signal[0]=(1-coeff)*signal[0]


