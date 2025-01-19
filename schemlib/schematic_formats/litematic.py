from datetime import datetime
from math import ceil, log2
from typing import Annotated, Any, Optional, Self, cast

from pydantic import BaseModel, Field, PlainSerializer, field_serializer, field_validator, model_validator
from PyMCTranslate import Version

from schemlib import nbt, snbt
from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic


class LitematicRegion(BaseModel, AbstractRegion):
    Size: BlockPos[nbt.Int]
    BlockStatePalette: nbt.List[BlockState]
    BlockStates: nbt.LongArray
    Entities: nbt.List[nbt.Compound] = Field(default_factory=nbt.List)
    PendingBlockTicks: nbt.List[nbt.Compound] = Field(default_factory=nbt.List)
    PendingFluidTicks: nbt.List[nbt.Compound] = Field(default_factory=nbt.List)
    Position: BlockPos[nbt.Int]
    TileEntities: nbt.List[nbt.Compound] = Field(default_factory=nbt.List)
    
    __minecraft_version__: Optional[Version] = None

    @field_validator("PendingBlockTicks", "PendingFluidTicks", mode="plain")
    @classmethod
    def validate_lists(cls, value):
        return nbt.List([nbt.Compound(x) for x in value])

    @field_validator("Entities", "TileEntities", mode="plain")
    @classmethod
    def validate_entities(cls, value):
        return nbt.List([entity.to_compound() if isinstance(entity, Entity) else entity for entity in value])

    @field_validator("BlockStatePalette", mode="plain")
    @classmethod
    def validate_blockstatepalette(cls, value):
        return nbt.List([BlockState.model_validate(x) for x in value])
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        matrix: dict[tuple[float, float, float], Entity] = {}
        for entity in self.Entities:
            matrix[tuple(entity["Pos"])] = Entity(entity)
        return matrix
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        matrix: dict[tuple[int, int, int], Entity] = {}
        for entity in self.TileEntities:
            matrix[(entity["x"], entity["y"], entity["z"])] = Entity(entity)
        return matrix
    
    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        (width, height, length) = self.Size.astuple()
        
        palette = {i: v for (i, v) in enumerate(self.BlockStatePalette)}
        
        blocks: dict[tuple[int, int, int], Block] = {}
        
        bits = nbt.LongArray.calcsize(len(palette))
        blockstates = self.BlockStates(bits, width * height * length)
        
        for x in range(abs(width)):
            for y in range(abs(height)):
                for z in range(abs(length)):
                    i = x + z * width + y * length * width
                    stateidx = blockstates[i]
                    if stateidx not in palette:
                        raise ValueError(x, y, z, i, stateidx)
                    state = palette[stateidx]
                    if state.Name == "minecraft:air":
                        continue
                    blocks[(x, y, z)] = Block(
                        pos=BlockPos(x=x, y=y, z=z),
                        state=state
                    )
            
        return blocks
    
    @property
    def minecraft_version(self) -> Version:
        if self.__minecraft_version__ is None:
            msg = f"{self.__class__.__name__} improperly initialized, missing Minecraft version"
            raise ValueError(msg)
        return self.__minecraft_version__
    
    @minecraft_version.setter
    def minecraft_version(self, value: Version):
        self.__minecraft_version__ = value
    
    def get_minecraft_version(self) -> Version:
        return self.minecraft_version

    def get_origin(self) -> BlockPos:
        return BlockPos.ORIGIN


class LitematicSchematic(BaseModel, AbstractSchematic):
    Metadata: "LitematicMetadata"
    Regions: nbt.Compound[LitematicRegion]
    Version: nbt.Int
    SubVersion: Optional[nbt.Int] = None
    MinecraftDataVersion: nbt.Int

    @field_validator("Regions", mode="plain")
    @classmethod
    def validate_regions(cls, value):
        return nbt.Compound({k: LitematicRegion.model_validate(v) for (k, v) in value.items()})
    
    class LitematicMetadata(BaseModel):
        Author: nbt.String
        Description: nbt.String
        Name: nbt.String
        RegionCount: nbt.Int
        TimeCreated: Annotated[datetime, PlainSerializer(lambda value: nbt.Long(value.timestamp() * 1000))]
        TimeModified: Annotated[datetime, PlainSerializer(lambda value: nbt.Long(value.timestamp() * 1000))]
        TotalBlocks: nbt.Int
        TotalVolume: nbt.Int
        EnclosingSize: BlockPos[nbt.Int]
        
        # @field_serializer("TimeCreated", "TimeModified", mode="plain")
        # def serialize_timestamp(self, value: datetime) -> nbt.Long:
        #     return nbt.Long(value.timestamp() * 1000)
        
        @field_validator("TimeCreated", "TimeModified", mode="plain")
        @classmethod
        def validate_timestamp(cls, value: Any) -> datetime:
            if isinstance(value, datetime):
                return value
            if not isinstance(value, nbt.Long):
                value = nbt.Long(value)
            return datetime.fromtimestamp(value / 1000)
        
    @model_validator(mode="after")
    def set_minecraft_version_on_regions(self):
        for region_name in self.Regions:
            self.Regions[region_name].minecraft_version = self.get_minecraft_version()
        return self
        
    @classmethod
    def get_default_extension(cls):
        return "litematic"

    @classmethod
    def get_default_version(cls) -> "Version":
        return cls.get_translation_manager().get_version("java", (1, 20, 1))
    
    @classmethod
    def get_format_description(cls) -> str:
        return "Litematica schematic (.litematic files)"

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
            
        return cls.model_validate(nbt.load_nbt_from_bytes(obj))
    
    def get_metadata(self) -> Any:
        return self.Metadata.model_dump(exclude_none=True)
    
    def get_minecraft_version(self):
        return self.get_translation_manager().get_version("java", self.MinecraftDataVersion)

    def get_name(self) -> str:
        return self.Metadata.Name or "unknown litematic schematic"
    
    def get_regions(self) -> list[AbstractRegion]:
        return list(self.Regions.values())
    
    @classmethod
    def from_schematic(cls, schematic: "AbstractSchematic", target_version: Optional["Version"]) -> Self:
        Metadata = schematic.get_metadata()
        
        regions = {}
        total_blocks = 0
        
        outer_p1 = (0, 0, 0)
        outer_p2 = (0, 0, 0)
        
        for (idx, region) in enumerate(schematic.get_regions()):
            pos1, pos2 = region.get_bounding_box()
            
            offset = (0, 0, 0)
            if pos1 != BlockPos.ORIGIN:
                offset = pos1.astuple()
                pos2 -= offset
                pos1 = BlockPos.ORIGIN
            
            outer_p1 = (
                min(outer_p1[0], pos1.x, pos2.x),
                min(outer_p1[1], pos1.y, pos2.y),
                min(outer_p1[2], pos1.z, pos2.z),
            )
            
            outer_p2 = (
                max(outer_p2[0], pos1.x, pos2.x),
                max(outer_p2[1], pos1.y, pos2.y),
                max(outer_p2[2], pos1.z, pos2.z),
            )
            
            (width, height, length) = region.get_size()
            (origin_x, origin_y, origin_z) = region.get_origin().astuple()
            
            if target_version is not None and target_version != schematic.get_minecraft_version():
                blocks = region.get_translated_blocks(target_version)
                entities = region.get_translated_entities(target_version)
                tile_entities = region.get_translated_tile_entities(target_version)
                palette = region.get_translated_palette(target_version)
            else:
                blocks = region.get_blocks()
                entities = region.get_entities()
                tile_entities = region.get_tile_entities()
                palette = region.get_palette()
                
            if BlockState.AIR_BLOCK in palette:
                air_block = palette.index(BlockState.AIR_BLOCK)
            else:
                air_block = 0
                palette.insert(0, BlockState.AIR_BLOCK)
            
            region_blocks = {}
            for block in blocks:
                if block.state.Name == "minecraft:air":
                    continue
                
                if block.state not in palette:
                    palette.append(block.state)
                    
                (x, y, z) = (block.pos - offset).astuple()
                    
                i = x + z * width + y * length * width
                # i = i = block.pos.x + block.pos.y * width + block.pos.z * height * width
                region_blocks[i] = palette.index(block.state)
                            
            volume = width * height * length
            regions[f"Converted Region {idx}"] = LitematicRegion.model_validate({
                "BlockStatePalette": palette,
                "BlockStates": nbt.LongArray.pack_list([region_blocks[i] if i in region_blocks else air_block for i in range(volume)]),
                "Entities": entities,
                "TileEntities": tile_entities,
                "Position": {
                    "x": origin_x,
                    "y": origin_y,
                    "z": origin_z,
                },
                "Size": {
                    "x": width,
                    "y": height,
                    "z": length,
                },
            })
            total_blocks += len(region_blocks)
            
        width = abs(outer_p2[0] - outer_p1[0]) + 1
        height = abs(outer_p2[1] - outer_p1[1]) + 1
        length = abs(outer_p2[2] - outer_p1[2]) + 1
            
        metadata = {
            "Name": "",
            "Author": "",
            "Description": "",
            "TimeCreated": datetime.now(),
            "TimeModified": datetime.now(),
            "RegionCount": len(regions),
            "TotalBlocks": total_blocks,
            "TotalVolume": width * height * length,
            "EnclosingSize": {
                "x": width,
                "y": height,
                "z": length,
            }
        }
        
        if name := schematic.get_name():
            metadata["Name"] = name
        if author := Metadata.get("author"):
            metadata["Author"] = author
        if date := Metadata.get("date"):
            metadata["TimeCreated"] = metadata["TimeModified"] = date
            
        if target_version is not None:
            minecraft_data_version = target_version.data_version
        else:
            minecraft_data_version = schematic.get_minecraft_version().data_version
            
        return cls.model_validate({
            "Metadata": metadata,
            "Regions": regions,
            "Version": 6,
            "SubVersion": 1,
            "MinecraftDataVersion": minecraft_data_version,
        })
        
    def schematic_dump(self):
        as_nbt = nbt.model_to_compound(self, "")
        return as_nbt.to_bytes(True)