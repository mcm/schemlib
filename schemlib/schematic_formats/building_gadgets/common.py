from typing import Optional

from pydantic import BaseModel, model_validator

from schemlib.blocks import BlockPos
from schemlib.nbt import Compound, Int
    
    
class BGBlockPos(BlockPos[Int]):
    @model_validator(mode="before")
    @classmethod
    def upper_case_compound_keys(cls, value):
        as_dict = {}
        
        if isinstance(value, BlockPos):
            return value.model_dump()
        
        for k in ("x", "y", "z"):
            if k in value:
                as_dict[k] = value[k]
            elif k.upper() in value:
                as_dict[k] = value[k.upper()]
        
        return Compound(as_dict)
    
    def model_dump_nbt(self, name: Optional[str]=None):
        return Compound({
            "X": self.x,
            "Y": self.y,
            "Z": self.z,
        })