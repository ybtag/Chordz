# Credits & Citations

Chordz builds on research and open-source work in Music Information Retrieval
(MIR). If you use Chordz in academic work, please cite the underlying tools.

## librosa
McFee, Brian, Colin Raffel, Dawen Liang, Daniel PW Ellis, Matt McVicar, Eric
Battenberg, and Oriol Nieto. 2015. "librosa: Audio and music signal analysis in
python." In *Proceedings of the 14th Python in Science Conference (SciPy)*,
18–25. ISC License. https://librosa.org (used: v0.11.0).

## madmom (optional ML backend)
Department of Computational Perception, Johannes Kepler University, Linz &
Austrian Research Institute for Artificial Intelligence (OFAI), Vienna.
https://github.com/CPJKU/madmom
- Source code: BSD-style license.
- Model/data files: Creative Commons Attribution-NonCommercial-ShareAlike 4.0
  (CC BY-NC-SA 4.0).
- Chord-related methods:
  - Korzeniowski, F., Böck, S., & Widmer, G. 2016. "Feature Learning for Chord
    Recognition: The Deep Chroma Extractor." *Proceedings of the 17th
    International Society for Music Information Retrieval Conference (ISMIR).*
  - Korzeniowski, F., & Widmer, G. 2016. "A Fully Convolutional Deep Auditory
    Model for Musical Chord Recognition." *IEEE International Workshop on
    Machine Learning for Signal Processing (MLSP).*

## Constant-Q Transform (feature background)
Brown, Judith C. 1991. "Calculation of a constant Q spectral transform."
*Journal of the Acoustical Society of America* 89(1): 425–434.
(Background summary via Wikipedia, CC BY-SA 4.0.)

## Creative Commons license reference
Creative Commons. "About the CC licenses" and "Frequently Asked Questions."
https://creativecommons.org/about/cclicenses/ and https://creativecommons.org/faq/
Content licensed CC BY 4.0. Used to characterize the NC/SA terms that apply to
madmom model files.

## Chordino / NNLS-Chroma (optional alternative)
Mauch, Matthias. 2010. "Automatic Chord Transcription from Audio Using
Computational Models of Musical Context." PhD thesis, Queen Mary University of
London.
Mauch, Matthias, and Simon Dixon. 2011. "Approximate note transcription for the
improved identification of difficult chords." *Proceedings of the 12th
International Society for Music Information Retrieval Conference (ISMIR).*
(Vamp plugin availability should be re-verified at install time.)

## PyInstaller (packaging)
PyInstaller documentation (public domain). https://pyinstaller.org (v6.21.0).

## Stage 2 -- HMM chord recognition (numpy-only)
Stage 2 uses a classic HMM chord recognizer with Krumhansl-Schmuckler key estimation and Viterbi decoding, implemented in pure numpy.

- Krumhansl, C. L. 1990. Cognitive Foundations of Musical Pitch. Oxford University Press. (key profiles.)
- Viterbi, A. J. 1967. Error bounds for convolutional codes and an asymptotically optimum decoding algorithm. IEEE Transactions on Information Theory 13(2): 260-269.
- Sheh, A., and Ellis, D. P. W. 2003. Chord segmentation and recognition using EM-trained hidden Markov models. Proceedings of ISMIR.

## madmom (NOT used -- documented decision)
madmom was the originally planned Stage 2 backend but is NOT used: its last release (0.16.1, 2018) has no wheels and does not build on modern Python 3.13+/3.14 with numpy 2.x. It is replaced by the numpy HMM above plus optional Demucs separation (Stage 2b, planned).
- Korzeniowski, F., Bock, S., and Widmer, G. 2016. Feature Learning for Chord Recognition: The Deep Chroma Extractor. ISMIR.

## Stage 2b (implemented, opt-in) -- Demucs source separation
- Defossez, A. Demucs: Music Source Separation. https://github.com/facebookresearch/demucs (MIT license.)
- Defossez, A., Usunier, N., Bottou, L. 2019. Music Source Separation in the Waveform Domain. arXiv:1909.13786.
- PyTorch. https://pytorch.org (BSD-style license.)

## Authorship
Vibe coded with GLM 5.2.
