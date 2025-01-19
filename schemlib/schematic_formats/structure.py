from typing import Annotated, Optional, Self, cast

from pydantic import BaseModel, Field, WrapSerializer, field_validator, model_validator
from PyMCTranslate import Version

# from schemlib import nbt
from schemlib.blocks import Block, BlockState, BlockPos
from schemlib.entities import Entity, EntityPos
from schemlib.nbt import Compound, Float, Int, List, load_nbt_from_bytes, model_to_compound
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic

class StructureBlockPos(BlockPos[Int]):
    @model_validator(mode="before")
    @classmethod
    def parse_list(cls, value):
        if isinstance(value, BlockPos):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        
        return Compound({
            "x": value[0],
            "y": value[1],
            "z": value[2],
        })
    
    def model_dump_nbt(self, name: Optional[str]=None):
        return List([self.x, self.y, self.z])
    
    @classmethod
    def from_block_pos(cls, blockpos: BlockPos):
        return cls(
            x=blockpos.x,
            y=blockpos.y,
            z=blockpos.z,
        )

class StructureEntityPos(EntityPos[Float]):
    @model_validator(mode="before")
    @classmethod
    def parse_list(cls, value):
        if isinstance(value, EntityPos):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        
        return Compound({
            "x": value[0],
            "y": value[1],
            "z": value[2],
        })
    
    def model_dump_nbt(self, name: Optional[str]=None):
        return List([self.x, self.y, self.z])
    
    @classmethod
    def from_entity_pos(cls, entitypos: EntityPos):
        return cls(
            x=entitypos.x,
            y=entitypos.y,
            z=entitypos.z,
        )
        
    
class StructureSchematicBlock(BaseModel):
    pos: StructureBlockPos
    nbt: Optional[Entity] = None
    state: Int
    
    def model_dump_nbt(self, name: Optional[str]=None):
        as_compound = Compound({
            "pos": model_to_compound(self.pos),
            "state": self.state
        })
        if self.nbt:
            as_compound["nbt"] = self.nbt.to_compound()
        return as_compound
    
    # @field_validator("pos", mode="wrap")
    # @classmethod
    # def validate_pos(cls, value, handler):
    #     if isinstance(value, list):
    #         value = {
    #             "x": Int(value[0]),
    #             "y": Int(value[1]),
    #             "z": Int(value[2]),
    #         }
    #     return handler(value)
    
    
class StructureSchematicEntity(BaseModel):
    blockPos: StructureBlockPos
    nbt: Entity
    pos: StructureEntityPos


class StructureSchematic(BaseModel, AbstractRegion, AbstractSchematic):
    DataVersion: Int
    blocks: List[StructureSchematicBlock]
    palette: List[BlockState]
    entities: List[StructureSchematicEntity]
    size: StructureBlockPos

    @field_validator("blocks", mode="plain")
    @classmethod
    def validate_blocks(cls, value):
        return List([StructureSchematicBlock.model_validate(x) for x in value])

    @field_validator("entities", mode="plain")
    @classmethod
    def validate_entities(cls, value):
        return List([StructureSchematicEntity.model_validate(x) for x in value])

    @field_validator("palette", mode="plain")
    @classmethod
    def validate_palette(cls, value):
        return List([BlockState.model_validate(x) for x in value])

    # @field_validator("entities", mode="plain")
    # @classmethod
    # def validate_entities(cls, value):
    #     return List([StructureSchematicEntity.model_validate(x) for x in value])

    # @field_validator("size", mode="wrap")
    # @classmethod
    # def validate_size(cls, value, handler):
    #     if isinstance(value, list):
    #         value = {
    #             "x": Int(value[0]),
    #             "y": Int(value[1]),
    #             "z": Int(value[2]),
    #         }
    #     return handler(value)
    
    @classmethod
    def get_format_description(cls) -> str:
        return "Create schematic / Minecraft structure (.nbt files)"

    @classmethod
    def get_default_extension(cls):
        return "nbt"

    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 20, 1))

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
            
        return cls.model_validate(load_nbt_from_bytes(obj))

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        matrix = {}
        
        for block in self.blocks:
            matrix[block.pos.astuple()] = Block(
                pos=block.pos,
                state=self.palette[block.state]
            )
            
        return matrix
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {entity.pos.astuple(): entity.nbt for entity in self.entities}
    
    def get_entities(self) -> list[Entity]:
        return [entity.nbt for entity in self.entities]
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {block.pos.astuple(): block.nbt for block in self.blocks if block.nbt}

    def get_origin(self) -> BlockPos:
        return BlockPos.ORIGIN

    def get_palette(self) -> list[BlockState]:
        return self.palette

    def get_size(self) -> tuple[int, int, int]:
        return self.size.astuple()

    def get_metadata(self):
        return {}

    def get_name(self) -> str:
        return "unknown nbt structure schematic"
    
    def get_regions(self) -> list[AbstractRegion]:
        return [self]
    
    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]) -> Self:
        if len(schematic.get_regions()) > 1:  # pragma: nocover
            msg = f"Too many regions in source schematic ({len(schematic.get_regions())})"
            raise ValueError(msg)
        
        if target_version:
            data_version = target_version.data_version
            source_palette = schematic.get_region(0).get_translated_palette(target_version)
            source_blocks = schematic.get_region(0).get_translated_blocks(target_version)
            source_entities = schematic.get_region(0).get_translated_entities(target_version)
            source_tile_entity_matrix = schematic.get_region(0).get_translated_tile_entity_matrix(target_version)
        else:
            data_version = schematic.get_minecraft_version().data_version
            source_palette = schematic.get_region(0).get_palette()
            source_blocks = schematic.get_region(0).get_blocks()
            source_entities = schematic.get_region(0).get_entities()
            source_tile_entity_matrix = schematic.get_region(0).get_tile_entity_matrix()
        
        blocks = []
        for source_block in source_blocks:
            block = {
                "pos": source_block.pos,
                "state": source_palette.index(source_block.state)
            }
            
            if source_block.pos.astuple() in source_tile_entity_matrix:
                block["nbt"] = source_tile_entity_matrix[source_block.pos.astuple()]
            
            blocks.append(block)
        
        return cls.model_validate({
            "DataVersion": data_version,
            "blocks": blocks,
            "palette": source_palette,
            "entities": [StructureSchematicEntity(
                blockPos=StructureBlockPos.from_block_pos(entity.blockPos), 
                nbt=entity, 
                pos=StructureEntityPos.from_entity_pos(entity.pos)
            ) for entity in source_entities],
            "size": schematic.get_region(0).get_size(),
        })
        
    def schematic_dump(self):
        as_nbt = model_to_compound(self, "")
        return as_nbt.to_bytes(True)

    def get_minecraft_version(self):
        return self.get_translation_manager().get_version("java", self.DataVersion)
