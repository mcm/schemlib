from typing import Any, Optional, Self, cast

from pydantic import BaseModel, Field, field_serializer
from PyMCTranslate import Version

from schemlib import nbt, snbt
from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic
from schemlib.schematic_formats.version_mapping import MinecraftVersion


class IntermediateRegion(BaseModel, AbstractRegion):
    minecraft_version: MinecraftVersion
    origin: BlockPos
    size: tuple[int, int, int]
    blocks: list[Block]
    entities: list[Entity] = Field(default_factory=list)
    tile_entities: list[Entity] = Field(default_factory=list)
    
    def get_minecraft_version(self) -> Version:
        return self.minecraft_version

    def get_origin(self) -> BlockPos:
        return self.origin

    def get_size(self) -> tuple[int, int, int]:
        return self.size

    def get_blocks(self) -> list[Block]:
        return self.blocks
    
    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        return {b.pos.astuple(): b for b in self.blocks}
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {entity.pos.astuple(): entity for entity in self.entities}
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {entity.blockPos.astuple(): entity for entity in self.tile_entities}

    def map_blocks(self, block_mapping: dict[str, str]):
        blocks = []
        for block in self.blocks:
            if block.state.Name in block_mapping:
                block.state.Name = block_mapping[block.state.Name]
            elif str(block.state) in block_mapping:
                block.state = BlockState.from_string(block_mapping[str(block.state)])
            blocks.append(block)
        self.blocks = blocks
        
    @classmethod
    def from_region(cls, region: AbstractRegion, target_version: Optional[Version]) -> "IntermediateRegion":
        if target_version is not None and target_version != region.get_minecraft_version():
            blocks = region.get_translated_blocks(target_version)
            entities = region.get_translated_entities(target_version)
            tile_entities = region.get_translated_tile_entities(target_version)
            minecraft_version = target_version
        else:
            blocks = region.get_blocks()
            entities = region.get_entities()
            tile_entities = region.get_tile_entities()
            minecraft_version = region.get_minecraft_version()

        if len(blocks) == 0:
            offset = BlockPos(x=0, y=0, z=0)
        else:
            offset = BlockPos(
                x=min([block.pos.x for block in blocks]),
                y=min([block.pos.y for block in blocks]),
                z=min([block.pos.z for block in blocks]),
            )

        for block in blocks:
            block.pos -= offset
            
        blocks = [b for b in blocks if b.state.Name != "minecraft:air"]
        
        return cls(
            origin=region.get_origin() - offset,
            size=region.get_size(),
            blocks=blocks,
            entities=entities,
            tile_entities=tile_entities,
            minecraft_version=minecraft_version,
        )


class IntermediateSchematic(BaseModel, AbstractSchematic):
    metadata: dict[str, Any]
    name: str
    regions: list[IntermediateRegion]
    minecraft_version: MinecraftVersion

    @classmethod
    def get_default_extension(cls) -> str:
        return "json"
    
    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 20, 1))
    
    @classmethod
    def get_format_description(cls) -> str:
        return "Generic Intermediate JSON Format"

    def get_metadata(self) -> Any:
        return self.metadata

    def get_name(self) -> str:
        return self.name
    
    def get_regions(self) -> list[AbstractRegion]:
        return cast(list[AbstractRegion], self.regions)

    def get_minecraft_version(self) -> Version:
        return self.minecraft_version
    
    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if isinstance(obj, str | bytes):
            return cls.model_validate_json(obj)
        return cls.model_validate(obj)

    def schematic_dump(self) -> str | bytes:
        return self.model_dump_json()

    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]) -> "IntermediateSchematic":
        regions = [IntermediateRegion.from_region(region, target_version) for region in schematic.get_regions()]
        
        if target_version:
            minecraft_version = target_version
        else:
            minecraft_version = schematic.get_minecraft_version()

        return cls(
            metadata=schematic.get_metadata(),
            name=schematic.get_name(),
            regions=regions,
            minecraft_version=minecraft_version
        )
