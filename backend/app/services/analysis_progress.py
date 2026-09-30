from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisProgress:
    """A coarse, privacy-neutral progress signal for one analysis run.

    Stages: ``profile`` (GitHub profile and repository list), ``repositories``
    (per-repository analysis, with ``completed`` out of ``total``) and
    ``interpretation`` (optional AI interpretation).
    """

    stage: str
    completed: int = 0
    total: int = 0


ProgressCallback = Callable[[AnalysisProgress], None]


def report_progress(
    callback: ProgressCallback | None,
    stage: str,
    completed: int = 0,
    total: int = 0,
) -> None:
    if callback is not None:
        callback(AnalysisProgress(stage=stage, completed=completed, total=total))
