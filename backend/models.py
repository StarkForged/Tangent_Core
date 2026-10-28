from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Config(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    columns: dict[str, str] = Field(default_factory=dict)
    failure_statuses: list[str] = Field(default_factory=lambda: ['failed', 'failure', 'error'])
    success_statuses: list[str] = Field(default_factory=lambda: ['success', 'completed', 'ok'])
    recurring_min: int = Field(3, ge=2, le=2000)
    contamination: float = Field(.05, ge=.001, le=.3)
    dbscan_eps: float = Field(.75, ge=.05, le=10)
    dbscan_min_samples: int = Field(3, ge=2, le=100)
    trend_interval: Literal['hour', 'day'] = 'hour'

    @model_validator(mode='after')
    def disjoint(self):
        self.failure_statuses = [s.strip().lower() for s in self.failure_statuses if s.strip()]
        self.success_statuses = [s.strip().lower() for s in self.success_statuses if s.strip()]
        if set(self.failure_statuses) & set(self.success_statuses):
            raise ValueError('Failure and success mappings must not overlap.')
        return self


class AnalysisRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=1, max_length=2000)
    config: Config = Field(default_factory=Config)
    synthetic: bool = False


class Finding(BaseModel):
    finding_id: str
    finding_type: Literal['recurring_failure', 'unusual_pattern', 'failure_cluster', 'exception_category']
    title: str
    observation: str
    affected_routes: list[str]
    observed_period: dict[str, str] | None
    reason_flagged: str
    interpretation: str
    record_count: int
    source_record_references: list[int]
    evidence: dict[str, Any]
    detection_method: str
    recommendations: list[str]
    limitations: list[str]


class Report(BaseModel):
    analysis_version: str = '1.1.0'
    synthetic: bool
    config: Config
    quality: dict[str, Any]
    summary: dict[str, Any]
    methods: dict[str, Any]
    findings: list[Finding]
    records: list[dict[str, Any]]
    excluded_records: list[dict[str, Any]] = Field(default_factory=list)
    distributions: dict[str, Any] = Field(default_factory=dict)
