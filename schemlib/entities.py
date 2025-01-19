from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler, SerializationInfo
from pydantic_core import core_schema

from schemlib import nbt, snbt
from schemlib.blocks import AbstractPos, BlockPos


class EntityPos[T: float](AbstractPos[T]):
    ORIGIN: ClassVar["EntityPos"]


EntityPos.ORIGIN = EntityPos(x=0.0, y=0.0, z=0.0)


class Entity:
    tag_type_id = 10
    __nbt: nbt.Compound
    
    def __init__(self, value: str | nbt.Compound):
        if isinstance(value, nbt.Compound):
            self.__nbt = value
        elif isinstance(value, dict):
            self.__nbt = nbt.Compound(value)
        else:
            self.__nbt = snbt.from_snbt(value)
            
    @property
    def pos(self) -> EntityPos[float]:
        (x, y, z) = self.__nbt.get("Pos") or EntityPos.ORIGIN.astuple()
        return EntityPos(x=x, y=y, z=z)
    
    @property
    def blockPos(self) -> BlockPos[int]:
        return BlockPos(
            x=int(self.pos.x),
            y=int(self.pos.y),
            z=int(self.pos.z),
        )
            
    def to_compound(self) -> nbt.Compound:
        return self.__nbt
    
    def to_bytes(self):
        return self.to_compound().to_bytes()
    
    def __str__(self):
        return snbt.to_snbt(self.__nbt)
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        from_str_schema = core_schema.chain_schema([
            core_schema.str_schema(),
            core_schema.no_info_plain_validator_function(cls)
        ])
        
        from_compound_schema = core_schema.chain_schema([
            handler(dict),
            core_schema.no_info_plain_validator_function(cls)
        ])
        
        from_python_schema = core_schema.union_schema([
            core_schema.is_instance_schema(cls),
            from_str_schema,
            from_compound_schema
        ])
        
        def serialize(value, info: SerializationInfo):
            if info.mode_is_json():
                return snbt.to_snbt(value.__nbt)
            return value.__nbt
        
        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=from_python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, info_arg=True)
        )