import os


def mne_templateMRI(verbose=True):
    """
    This function is a helper that returns the path of the MRI template for adults (the ``src`` and the
    ``bem``) that is made available through ``MNE``. It downloads the data if need be. These templates can be used for EEG source reconstruction
    when no individual MRI is available.

    See https://mne.tools/stable/auto_tutorials/forward/35_eeg_no_mri.html

    Examples
    ---------
    >>> import neurokit2 as nk
    >>>
    >>> src, bem = nk.mne_templateMRI()
    """

    # Try loading pooch (needed by mne)
    try:
        import pooch
    except ImportError as e:
        raise ImportError(
            "The 'pooch' module is required for this function to run. ",
            "Please install it first (`pip install pooch`).",
        ) from e

    # Try loading mne
    try:
        import mne
    except ImportError as e:
        raise ImportError(
            "NeuroKit error: mne_templateMRI(): the 'mne' module is required for this function to run. ",
            "Please install it first (`pip install mne`).",
        ) from e

    # Download fsaverage files
    fs_dir = mne.datasets.fetch_fsaverage(verbose=verbose)
    subjects_dir = os.path.dirname(fs_dir)

    # The files live in:
    src = os.path.join(fs_dir, "bem", "fsaverage-ico-5-src.fif")
    bem = os.path.join(fs_dir, "bem", "fsaverage-5120-5120-5120-bem-sol.fif")
    return src, bem
