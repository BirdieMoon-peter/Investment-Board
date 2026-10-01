"""Source controls accept only the effective enabled flag."""
from pydantic import BaseModel, ConfigDict, StrictBool


class DataSourceUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: StrictBool
