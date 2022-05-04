# -*- coding: utf-8 -*-
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..misc import expspace


def fractal_dfa(
    signal,
    scale="default",
    overlap=True,
    integrate=True,
    order=1,
    multifractal=False,
    q="default",
    show=False,
    **kwargs,
):
    """**(Multifractal) Detrended Fluctuation Analysis (DFA or MFDFA)**

    Detrended fluctuation analysis, much like the Hurst exponent, is used to find long-term
    statistical dependencies in time series.

    For monofractal DFA, the output *alpha* :math:`\\alpha` corresponds to the slope of the linear
    trend between the scale factors and the fluctuations. For multifractal DFA, the slope values
    under different *q* values are actually generalised Hurst exponents *h*.

    The output is for multifractal DFA is a dataframe containing the following features:

    * TODO.

    This function can be called either via ``fractal_dfa()`` or ``complexity_dfa()``, and its
    multifractal variant can be directly accessed via ``fractal_mfdfa()`` or ``complexity_mfdfa()``.

    Parameters
    ----------
    signal : Union[list, np.array, pd.Series]
        The signal (i.e., a time series) in the form of a vector of values.
    scale : list
        A list containing the lengths of the windows (number of data points in each subseries) that
        the signal is divided into. Also referred to as Tau :math:`\\tau`. If ``"default"``, will
        set it to a logarithmic scale (so that each window scale has the same weight) with a
        minimum of 4 and maximum of a tenth of the length (to have more than 10 windows to
        calculate the average fluctuation).
    overlap : bool
        Defaults to ``True``, where the windows will have a 50% overlap with each other, otherwise
        non-overlapping windows will be used.
    integrate : bool
        It is common practice to convert the signal to a random walk (i.e., detrend and integrate,
        which corresponds to the signal 'profile'). Note that it leads to the flattening of the
        signal, which can lead to the loss of some details (see Ihlen, 2012 for an explanation).
        Note that for strongly anticorrelated signals, this transformation should be applied  two
        times (i.e., provide ``np.cumsum(signal - np.mean(signal))`` instead of `signal`).
    order : int
       The order of the polynomial trend for detrending, 1 for the linear trend.
    multifractal : bool
        If true, compute Multifractal Detrended Fluctuation Analysis (MFDFA), in which case the
        argument ``q`` is taken into account.
    q : Union[int, list, np.array]
        The sequence of fractal exponents when ``multifractal=True``. Must be a sequence between
        -10 and 10 (note that zero will be removed, since the code does not converge there).
        Setting ``q = 2`` (default for DFA) gives a result of a standard DFA. For instance, Ihlen
        (2012) uses ``q = [-5, -3, -1, 0, 1, 3, 5]`` (default when for multifractal). In general,
        positive q moments amplify the contribution of fractal components with larger amplitude and
        negative q moments amplify the contribution of fractal with smaller amplitude (Kantelhardt
        et al., 2002).
    show : bool
        Visualise the trend between the window size and the fluctuations.
    **kwargs : optional
        Currently not used.

    Returns
    ----------
    dfa : float or np.array
        If `multifractal` is False, one DFA value is returned for a single time series.
    parameters : dict
        A dictionary containing additional information regarding the parameters used
        to compute DFA. If `multifractal` is False, the dictionary contains q value, a
        series of windows, fluctuations of each window and the
        slopes value of the log2(windows) versus log2(fluctuations) plot. If
        `multifractal` is True, the dictionary additionally contains the
        parameters of the singularity spectrum (scaling exponents, singularity dimension,
        singularity strength; see `_singularity_spectrum()` for more information).

    See Also
    --------
    fractal_hurst

    Examples
    ----------
    **Example 1:** Monofractal DFA
    .. ipython:: python

      import neurokit2 as nk

      signal = nk.signal_simulate(duration=10, frequency=[5, 7, 10, 14], noise=0.05)

      @savefig p_fractal_dfa1.png scale=100%
      dfa, info = nk.fractal_dfa(signal, show=True)
      @suppress
      plt.close()

    .. ipython:: python

      dfa


    As we can see from the plot, the final value, corresponding to the slope of the red line,
    doesn't capture properly the relationship. We can adust the *scale factors* to capture the
    fractality of short-term fluctuations.

    .. ipython:: python

      scale = nk.expspace(10, 100, 20, base=2)

      @savefig p_fractal_dfa2.png scale=100%
      dfa, info = nk.fractal_dfa(signal, scale=scale, show=True)
      @suppress
      plt.close()

    **MFDFA**
    .. ipython:: python

      @savefig p_fractal_dfa3.png scale=100%
      mfdfa, info = nk.fractal_mfdfa(signal, q=[-5, -3, -1, 0, 1, 3, 5], show=True)
      @suppress
      plt.close()

    .. ipython:: python

      mfdfa

    References
    -----------
    * Ihlen, E. A. F. E. (2012). Introduction to multifractal detrended
      fluctuation analysis in Matlab. Frontiers in physiology, 3, 141.
    * Kantelhardt, J. W., Zschiegner, S. A., Koscielny-Bunde, E., Havlin, S.,
      Bunde, A., & Stanley, H. E. (2002). Multifractal detrended fluctuation
      analysis of nonstationary time series. Physica A: Statistical
      Mechanics and its Applications, 316(1-4), 87-114.
    * Hardstone, R., Poil, S. S., Schiavone, G., Jansen, R., Nikulin, V. V.,
      Mansvelder, H. D., & Linkenkaer-Hansen, K. (2012). Detrended
      fluctuation analysis: a scale-free view on neuronal oscillations.
      Frontiers in physiology, 3, 450.

    """
    # Sanity checks
    if isinstance(signal, (np.ndarray, pd.DataFrame)) and signal.ndim > 1:
        raise ValueError(
            "Multidimensional inputs (e.g., matrices or multichannel data) are not supported yet."
        )

    n = len(signal)
    scale = _fractal_dfa_findscales(n, scale)

    # Sanitize fractal power (cannot be close to 0)
    q = _sanitize_q(q, multifractal=multifractal)

    # Store parameters
    info = {"scale": scale, "q": q[:, 0]}

    # Preprocessing
    if integrate is True:
        # Get signal profile
        signal = np.cumsum(signal - np.mean(signal))

    # Function to store fluctuations. For DFA this is an array. For MFDFA, this
    # is a matrix of size (len(scale),len(q))
    fluctuations = np.zeros((len(scale), len(q)))

    # Start looping over scale
    for i, window in enumerate(scale):

        # Get window
        segments = _fractal_dfa_getwindow(signal, n, window, overlap=overlap)

        # Get polynomial trends
        trends = _fractal_dfa_trends(segments, window, order=order)

        # Get local fluctuation
        fluctuations[i] = _fractal_dfa_fluctuation(segments, trends, multifractal, q)

    # I would not advise the next part part. I understand the need to remove zeros, but I
    # would instead suggest masking it with numpy.ma masked arrays. Note that
    # when 'q' is a list,  scale[nonzero] increases in size.

    # Filter zeros
    # nonzero = np.nonzero(fluctuations)[0]
    # scale = scale[nonzero]
    # fluctuations = fluctuations[nonzero]

    if len(fluctuations) == 0:
        return np.nan, info

    # Get slopes
    slopes = _slopes(scale, fluctuations, q)
    if len(slopes) == 1:
        slopes = slopes[0]

    # Prepare output
    info["Fluctuation"] = fluctuations
    info["Alpha"] = slopes

    # Extract features
    if multifractal is True:
        info.update(_singularity_spectrum(q=q, slopes=slopes))
        out = {
            k: v
            for k, v in info.items()
            if k in ["ExpRange", "ExpMean", "DimRange", "DimMean", "HMax", "HDelta", "HAR"]
        }
        out = pd.DataFrame(out, index=[0])
    else:
        out = slopes

    # Plot if show is True.
    if show is True:
        if multifractal is True:
            _fractal_mdfa_plot(
                info,
                scale=scale,
                fluctuations=fluctuations,
                q=q,
            )
        else:
            _fractal_dfa_plot(info=info, scale=scale, fluctuations=fluctuations)

    return out, info


# =============================================================================
#  Utils MFDFA
# =============================================================================
def _singularity_spectrum(q, slopes):
    """Extract the slopes of the fluctuation function to futher obtain the
    singularity strength `α` (or Hölder exponents) and singularity spectrum
    `f(α)` (or fractal dimension). This is iconically shaped as an inverse
    parabola, but most often it is difficult to obtain the negative `q` terms,
    and one can focus on the left side of the parabola (`q>0`).

    Note that these measures rarely match the theoretical expectation,
    thus a variation of ± 0.25 is absolutely reasonable.

    The parameters are mostly identical to `fractal_mfdfa()`, as one needs to
    perform MFDFA to obtain the singularity spectrum. Calculating only the
    DFA is insufficient, as it only has `q=2`, and a set of `q` values are
    needed. Here defaulted to `q = list(range(-5,5))`, where the `0` element
    is removed by `_cleanse_q()`.

    Returns
    -------
    tau: np.array
        Scaling exponents `τ`. A usually increasing function of `q` from
        which the fractality of the data can be determined by its shape. A truly
        linear tau indicates monofractality, whereas a curved one (usually
        curving around small `q` values) indicates multifractality.
    Hq: np.array
        Singularity strength `H`. The width of this function indicates the
        strength of the multifractality. A width of `max(H) - min(H) ≈ 0`
        means the data is monofractal.
    Dq: np.array
        Singularity spectrum `Dq`. The location of the maximum of `Dq` (with
        `H` as the abscissa) should be 1 and indicates the most prominent
        exponent in the data.

    Notes
    -----
    This was first designed and implemented by Leonardo Rydin in
    `MFDFA <https://github.com/LRydin/MFDFA/>`_ and ported here by the same.
    """
    # The generalised Hurst exponents `h(q)` from MFDFA, which are simply the slopes of each DFA
    # for various `q` values
    out = {"h": slopes}

    # Calculate the Scaling Exponent Tau
    # https://github.com/LRydin/MFDFA/issues/30
    out["Tau"] = q[:, 0] * slopes - 1

    # Calculate Singularity Exponent H or α, which needs tau
    out["H"] = np.gradient(out["Tau"]) / np.gradient(q[:, 0])

    # Calculate Singularity Dimension Dq or f(α), which needs tau and q
    # The relation between α and f(α) is called the Multifractal (MF) spectrum or singularity
    # spectrum
    out["D"] = q[:, 0] * out["H"] - out["Tau"]

    # Calculate the singularity
    out["ExpRange"] = np.nanmax(out["H"]) - np.nanmin(out["H"])
    out["ExpMean"] = np.nanmean(out["H"])
    out["DimRange"] = np.nanmax(out["D"]) - np.nanmin(out["D"])
    out["DimMean"] = np.nanmean(out["D"])

    # Features (Orozco-Duque et al., 2015)
    # the singularity exponent, for which the spectrum takes its
    # maximum value (α0)
    out["HMax"] = out["H"][np.nanargmax(out["D"])]
    # the spectrum width delta
    out["HDelta"] = np.nanmax(out["H"]) - np.nanmin(out["H"])
    # the asymmetric ratio (AR) defined as the ratio between h calculated with negative q and the
    # total width of the spectrum. If the multifractal spectrum is symmetric, AR should be equal to
    # 0.5
    out["HAR"] = (np.nanmin(out["H"]) - out["HMax"]) / out["HDelta"]

    # h-fluctuation index (hFI), which is defined as the power of the second derivative of h(q)
    # hFI tends to zero in high fractionation signals. hFI has no reference point when a set of
    # signals is evaluated, so hFI must be normalised, so that hFIn = 1 is the most organised and
    # the most regular signal in the set
    # TODO.

    return out


# =============================================================================
#  Utils
# =============================================================================
def _sanitize_q(q=2, multifractal=False):
    # TODO: Add log calculator for q ≈ 0

    # Enforce DFA in case 'multifractal = False' but 'q' is not 2
    if isinstance(q, str):
        if multifractal is False:
            q = 2
        else:
            q = [-5, -3, -1, 0, 1, 3, 5]

    # Fractal powers as floats
    q = np.asarray_chkfinite(q, dtype=float)

    # Ensure q≈0 is removed, since it does not converge. Limit set at |q| < 0.1
    q = q[(q < -0.1) + (q > 0.1)]

    # Reshape q to perform np.float_power
    q = q.reshape(-1, 1)

    return q


def _slopes(scale, fluctuations, q):
    # Extract the slopes of each `q` power obtained with MFDFA to later produce
    # either the singularity spectrum or the multifractal exponents.
    # Note: added by Leonardo Rydin (see https://github.com/LRydin/MFDFA/)

    # Ensure mfdfa has the same q-power entries as q
    if fluctuations.shape[1] != q.shape[0]:
        raise ValueError("Fluctuation function and q powers don't match in dimension.")

    # Allocated array for slopes
    slopes = np.zeros(len(q))
    # Find slopes of each q-power
    for i in range(len(q)):
        # if fluctiations is zero, log2 wil encounter zero division
        old_setting = np.seterr(divide="ignore", invalid="ignore")
        slopes[i] = np.polyfit(np.log2(scale), np.log2(fluctuations[:, i]), 1)[0]
        np.seterr(**old_setting)

    return slopes


def _fractal_dfa_findscales(n, scale="default"):
    # Convert to array
    if isinstance(scale, list):
        scale = np.asarray(scale)

    # Default scale number
    if scale is None or isinstance(scale, str):
        scale = int(n / 10)

    # See https://github.com/neuropsychology/NeuroKit/issues/206
    if isinstance(scale, int):
        scale = expspace(10, int(n / 10), scale, base=2)
        scale = np.unique(scale)  # keep only unique

    # Sanity checks (return warning for too short scale)
    if len(scale) < 2:
        raise ValueError("NeuroKit error: more than one window is needed. Increase 'scale'.")

    if np.min(scale) < 2:
        raise ValueError(
            "NeuroKit error: there must be at least 2 data points in each window. Decrease 'scale'."
        )
    if np.max(scale) >= n:
        raise ValueError(
            "NeuroKit error: the window cannot contain more data points than the time series. Decrease 'scale'."
        )

    return scale


def _fractal_dfa_getwindow(signal, n, window, overlap=True):
    # This function reshapes the segments from a one-dimensional array to a
    # matrix for faster polynomail fittings. 'Overlap' reshapes into several
    # overlapping partitions of the data

    if overlap:
        segments = np.array([signal[i : i + window] for i in np.arange(0, n - window, window // 2)])
    else:
        segments = signal[: n - (n % window)]
        segments = segments.reshape((signal.shape[0] // window, window))

    return segments


def _fractal_dfa_trends(segments, window, order=1):
    x = np.arange(window)

    coefs = np.polyfit(x[:window], segments.T, order).T

    # TODO: Could this be optimized? Something like np.polyval(x[:window], coefs)
    trends = np.array([np.polyval(coefs[j], x) for j in np.arange(len(segments))])

    return trends


def _fractal_dfa_fluctuation(segments, trends, multifractal=False, q=2):

    detrended = segments - trends

    if multifractal is True:
        var = np.var(detrended, axis=1)
        # obtain the fluctuation function, which is a function of the windows
        # and of q
        # ignore division by 0 warning
        old_setting = np.seterr(divide="ignore", invalid="ignore")
        fluctuation = np.float_power(np.mean(np.float_power(var, q / 2), axis=1), 1 / q.T)
        np.seterr(**old_setting)

    else:
        # Compute Root Mean Square (RMS)
        fluctuation = np.sum(detrended ** 2, axis=1) / detrended.shape[1]
        fluctuation = np.sqrt(np.sum(fluctuation) / len(fluctuation))

    return fluctuation


# =============================================================================
#  Plots
# =============================================================================
def _fractal_dfa_plot(info, scale, fluctuations):

    polyfit = np.polyfit(np.log2(scale), np.log2(fluctuations), 1)
    fluctfit = 2 ** np.polyval(polyfit, np.log2(scale))
    plt.loglog(scale, fluctuations, "o", c="#90A4AE")
    plt.xlabel(r"$\log_{2}$(Scale)")
    plt.ylabel(r"$\log_{2}$(Fluctuation)")
    plt.loglog(scale, fluctfit, c="#E91E63", label=r"$\alpha$ = {:.3f}".format(info["Alpha"]))

    plt.legend(loc="lower right")
    plt.title("Detrended Fluctuation Analysis (DFA)")

    return None


def _fractal_mdfa_plot(info, scale, fluctuations, q):

    # Prepare figure
    fig = plt.figure(constrained_layout=False)
    spec = matplotlib.gridspec.GridSpec(ncols=2, nrows=2)

    ax_fluctuation = fig.add_subplot(spec[0, 0])
    ax_spectrum = fig.add_subplot(spec[0, 1])
    ax_tau = fig.add_subplot(spec[1, 0])
    ax_hq = fig.add_subplot(spec[1, 1])

    n = len(q)
    colors = plt.cm.plasma(np.linspace(0, 1, n))

    # Plot the points
    for i in range(len(q)):
        polyfit = np.polyfit(np.log2(scale), np.log2(fluctuations[:, i]), 1)
        ax_fluctuation.loglog(scale, fluctuations, "o", c="#d2dade", markersize=5, base=2)
    # Plot the polyfit line
    for i in range(len(q)):
        polyfit = np.polyfit(np.log2(scale), np.log2(fluctuations[:, i]), 1)
        # Label max and min
        if i == 0:
            ax_fluctuation.plot(
                [],
                label=(r"$h$ = {:.3f}, $q$ = {:.1f}").format(polyfit[0], q[0][0]),
                c=colors[0],
            )
        elif i == (len(q) - 1):
            ax_fluctuation.plot(
                [],
                label=(r"$h$ = {:.3f}, $q$ = {:.1f}").format(polyfit[0], q[-1][0]),
                c=colors[-1],
            )
        fluctfit = 2 ** np.polyval(polyfit, np.log2(scale))
        ax_fluctuation.loglog(scale, fluctfit, c=colors[i], base=2, label="_no_legend_")

    ax_fluctuation.set_xlabel(r"$\log_{2}$(Scale)")
    ax_fluctuation.set_ylabel(r"$\log_{2}$(Fluctuation)")
    ax_fluctuation.legend(loc="lower right")

    # Plot the singularity spectrum
    # ax.set_title("Singularity Spectrum")
    ax_spectrum.set_ylabel(r"Singularity Dimension ($D$)")
    ax_spectrum.set_xlabel(r"Singularity Exponent ($H$)")
    ax_spectrum.axvline(
        x=info["HMax"],
        color="black",
        linestyle="dashed",
        label=r"HMax = {:.3f}".format(info["HMax"]),
    )
    ax_spectrum.plot(info["H"], info["D"], "o-", c="#FFC107")
    ax_spectrum.legend(loc="lower right")

    # Plot tau against q
    # ax.set_title("Scaling Exponents")
    ax_tau.set_ylabel(r"Scaling Exponent ($τ$)")
    ax_tau.set_xlabel(r"Fractal Exponent ($q$)")
    ax_tau.plot(q, info["Tau"], "o-", c="#E91E63")

    # Plot H against q
    # ax.set_title("Generalised Hurst Exponents")
    ax_hq.set_ylabel(r"Singularity Exponent ($H$)")
    ax_hq.set_xlabel(r"Fractal Exponent ($q$)")
    ax_hq.plot(q, info["H"], "o-", c="#2196F3")

    fig.suptitle("Multifractal Detrended Fluctuation Analysis (MFDFA)")

    return None
