from typing import Optional, Self, cast

from pydantic import BaseModel, field_validator
from PyMCTranslate import Version

# from schemlib import nbt
from schemlib.blocks import Block, BlockState, BlockPos
from schemlib.entities import Entity, EntityPos
from schemlib.nbt import Byte, Compound, Int, IntArray, List, Short, String, load_nbt_from_bytes, model_to_compound
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic


class StructurizeOptionalData(BaseModel):
    primary_offset: BlockPos
    
    
class OptionalData(BaseModel):
    structurize: StructurizeOptionalData


class StructurizeBlueprint(BaseModel, AbstractRegion, AbstractSchematic):
    architects: Optional[List[String]] = None
    blocks: IntArray
    entities: List[Compound]
    mcversion: Optional[Int] = None
    name: String
    optional_data: Optional[OptionalData] = None
    palette: List[BlockState]
    required_mods: List[String]
    size_x: Short
    size_y: Short
    size_z: Short
    tile_entities: List[Compound]
    version: Byte

    # @field_validator("entities", mode="plain")
    # @classmethod
    # def validate_entities(cls, value):
    #     return List([StructureSchematicEntity.model_validate(x) for x in value])

    @field_validator("palette", mode="plain")
    @classmethod
    def validate_palette(cls, value):
        return List([BlockState.model_validate(x) for x in value])
    
    @classmethod
    def get_format_description(cls) -> str:
        return "Structurize / MineColonies Blueprint (.blueprint files)"

    @classmethod
    def get_default_extension(cls):
        return "blueprint"

    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 12, 2))

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
            
        return cls.model_validate(load_nbt_from_bytes(obj))

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        matrix = {}
        
        blockstates = self.blocks.asarray("uint16")
        
        for y in range(self.size_y):
            for z in range(self.size_z):
                for x in range(self.size_x):
                    idx = y * self.size_z * self.size_x + z * self.size_x + x
                    
                    state = self.palette[blockstates[idx]]
                    
                    if state.Name == "minecraft:air":
                        continue
                    if state.Name.startswith("structurize") and state.Name.endswith("substitution"):
                        continue
                    
                    matrix[(x, y, z)] = Block(
                        pos=BlockPos(x=x, y=y, z=z),
                        state=state
                    )
                    
        return matrix
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {}
        # return {entity.pos.astuple(): entity.nbt for entity in self.entities}
    
    def get_entities(self) -> list[Entity]:
        return []
        # return [entity.nbt for entity in self.entities]
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {}
        # return {block.pos.astuple(): block.nbt for block in self.blocks if block.nbt}

    def get_origin(self) -> BlockPos:
        return BlockPos.ORIGIN

    def get_palette(self) -> list[BlockState]:
        palette = []
        for state in self.palette:
            if state.Name == "minecraft:air":
                continue
            if state.Name.startswith("structurize:") and state.Name.endswith("substitution"):
                continue
            palette.append(state)
        return palette

    def get_size(self) -> tuple[int, int, int]:
        return (self.size_x, self.size_y, self.size_z)

    def get_metadata(self):
        return {}

    def get_name(self) -> str:
        return self.name
    
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
            source_block_matrix = schematic.get_region(0).get_translated_block_matrix(target_version)
            source_entities = schematic.get_region(0).get_translated_entities(target_version)
            source_tile_entities = schematic.get_region(0).get_translated_tile_entities(target_version)
        else:
            data_version = schematic.get_minecraft_version().data_version
            source_palette = schematic.get_region(0).get_palette()
            source_block_matrix = schematic.get_region(0).get_block_matrix()
            source_entities = schematic.get_region(0).get_entities()
            source_tile_entities = schematic.get_region(0).get_tile_entities()
            
        (width, height, length) = schematic.get_region(0).get_size()
        
        if BlockState.AIR_BLOCK in source_palette:
            airBlock = source_palette.index(BlockState.AIR_BLOCK)
        else:
            source_palette.insert(0, BlockState.AIR_BLOCK)
            airBlock = 0
        
        blocks = []
        required_mods = []
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    if (x, y, z) in source_block_matrix:
                        block = source_block_matrix[(x, y, z)]
                    
                        modid, _, _ = block.state.Name.partition(":")
                        if modid != "minecraft" and modid not in required_mods:
                            required_mods.append(modid)
                            
                        stateidx = source_palette.index(block.state)
                    else:
                        stateidx = airBlock
                    
                    blocks.append(stateidx)
                    
        data = {
            # "architects": None,
            "blocks": IntArray.pack_list(blocks, width=16),
            "entities": source_entities,
            "mcversion": data_version,
            "name": schematic.get_name(),
            "palette": source_palette,
            "required_mods": required_mods,
            "size_x": width,
            "size_y": height,
            "size_z": length,
            "tile_entities": source_tile_entities,
            "version": 1,
        }
        # TODO: Add author
        
        return cls.model_validate(data)
        
    def schematic_dump(self):
        as_nbt = model_to_compound(self, "")
        return as_nbt.to_bytes(True)

    def get_minecraft_version(self):
        if self.mcversion is None:
            return self.get_default_version()
        return self.get_translation_manager().get_version("java", self.mcversion)
