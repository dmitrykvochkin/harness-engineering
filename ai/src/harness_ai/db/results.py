"""Turn classifier JSONL (`results.jsonl`) into `signals` table rows.

A null signal with an entry in `errors` becomes verdict `error`. The three
signal names always produce a row, so a failed detector stays visible.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from harness_ai.dataset.labels import Signal
from harness_ai.db.rows import DetectorVerdict, SignalRow

SIGNAL_TYPES = (Signal.USER_FRUSTRATION, Signal.TASK_FAILURE, Signal.FORGETTING)
ClassificationVerdict = Literal["present", "absent", "insufficient_evidence"]


class Classification(BaseModel):
    verdict: ClassificationVerdict
    reason: str = Field(min_length=1)
    evidence_event_ids: list[str] = Field(default_factory=list)


class ResultRecord(BaseModel):
    run_id: str
    model: str = Field(min_length=1)
    signals: dict[str, Classification | None]
    errors: dict[str, str] = Field(default_factory=dict)


def rows_from_record(record: ResultRecord) -> list[SignalRow]:
    rows: list[SignalRow] = []
    for signal in SIGNAL_TYPES:
        finding = record.signals.get(signal.value)
        if finding is None:
            message = record.errors.get(signal.value, "").strip() or "Detector failed"
            rows.append(
                SignalRow(
                    run_id=record.run_id,
                    signal_type=signal,
                    verdict=DetectorVerdict.ERROR,
                    explanation=message,
                    detector_version=record.model,
                )
            )
            continue
        rows.append(
            SignalRow(
                run_id=record.run_id,
                signal_type=signal,
                verdict=DetectorVerdict(finding.verdict),
                explanation=finding.reason,
                evidence_event_ids=finding.evidence_event_ids,
                detector_version=record.model,
            )
        )
    return rows


def load_result_rows(path: Path) -> list[SignalRow]:
    rows: list[SignalRow] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = ResultRecord.model_validate_json(line)
        except ValidationError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
        rows.extend(rows_from_record(record))
    return rows
