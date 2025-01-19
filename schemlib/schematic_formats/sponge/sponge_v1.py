from datetime import datetime
from typing import Annotated, Any, Optional, Self

from pydantic import BaseModel, Field, PlainSerializer, field_validator
from PyMCTranslate import Version

from schemlib import nbt
from schemlib.blocks import Block, BlockState, BlockPos
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic


class SpongeSchematicMetadata(BaseModel):
    Name: Optional[nbt.String] = Field(default=None)
    Author: Optional[nbt.String] = Field(default=None)
    # Date: Annotated[datetime, PlainSerializer(lambda value: nbt.Long(value.timestamp() * 1000))] = Field(default=datetime.now())
    Date: Optional[datetime] = Field(default=None)
    RequiredMods: Optional[nbt.List[nbt.String]] = Field(default=None)
    
    @field_validator("RequiredMods", mode="after")
    @classmethod
    def validate_required_mods(cls, value):
        if value is None:
            return value
        return nbt.List([nbt.String(x) for x in value])
    
    def model_dump_nbt(self, name: Optional[str]=""):
        as_dict = {}
        if self.Name:
            as_dict["Name"] = self.Name
        if self.Author:
            as_dict["Author"] = self.Author
        if self.Date:
            as_dict["Date"] = nbt.Long(self.Date.timestamp() * 1000)
        if self.RequiredMods:
            as_dict["RequiredMods"] = self.RequiredMods
        return nbt.Compound(as_dict)
        
    @field_validator("Date", mode="plain")
    @classmethod
    def validate_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, nbt.Long):
            value = nbt.Long(value)
        return datetime.fromtimestamp(value / 1000)


class SpongeSchematicV1(BaseModel, AbstractRegion, AbstractSchematic):
    Version: nbt.Int
    Metadata: SpongeSchematicMetadata
    Width: nbt.Short
    Height: nbt.Short
    Length: nbt.Short
    Offset: nbt.IntArray
    PaletteMax: nbt.Int
    Palette: nbt.Compound[nbt.Int]
    BlockData: nbt.ByteArray
    TileEntities: nbt.List[Entity] = Field(default_factory=nbt.List)
    
    @field_validator("Palette", mode="plain")
    @classmethod
    def validate_palette(cls, value):
        return nbt.Compound({k: nbt.Int(v) for (k, v) in value.items()})
    
    @classmethod
    def get_format_description(cls) -> str:
        return "Sponge v1 (.schem files)"

    @classmethod
    def get_default_extension(cls):
        return "schem"

    @classmethod
    def get_default_version(cls) -> "Version":
        return cls.get_translation_manager().get_version("java", (1, 13, 2))

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
            
        return cls.model_validate(nbt.load_nbt_from_bytes(obj))
    
    def _get_palette(self) -> dict[int, BlockState]:
        return {v: BlockState.from_string(k) for (k, v) in self.Palette.items()}
    
    def get_palette(self) -> list[BlockState]:
        return list(self._get_palette().values())

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        palette = self._get_palette()
        
        blocks: dict[tuple[int, int, int], Block] = {}
        for i, block in enumerate(self.BlockData):
            x = (i % self.Width) - self.Offset[0]
            i = (i - x) // self.Width
            z = (i % self.Length) - self.Offset[1]
            y = ((i - z) // self.Length) - self.Offset[2]
            
            blocks[(x, y, z)] = Block(
                pos=BlockPos(x=x, y=y, z=z),
                state=palette[block & 0xFF]
            )
        return blocks
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {}
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {entity.pos.astuple(): entity for entity in self.TileEntities}

    def get_origin(self) -> BlockPos:
        return BlockPos.ORIGIN

    def get_size(self) -> tuple[int, int, int]:
        return (self.Width, self.Height, self.Length)

    def get_metadata(self):
        return {
            "author": self.Metadata.Author,
            "date": self.Metadata.Date or datetime.now()
        }

    def get_name(self) -> str:
        if self.Metadata.Name:
            return self.Metadata.Name
        return f"unknown sponge schematic, v{self.Version}"
    
    def get_regions(self) -> list[AbstractRegion]:
        return [self]
    
    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional["Version"]) -> Self:
        if len(schematic.get_regions()) > 1:  # pragma: nocover
            msg = f"Too many regions in source schematic ({len(schematic.get_regions())})"
            raise ValueError(msg)
        
        if target_version:
            source_palette = schematic.get_region(0).get_translated_palette(target_version)
            source_blocks = schematic.get_region(0).get_translated_blocks(target_version)
            source_entities = schematic.get_region(0).get_translated_entities(target_version)
        else:
            source_palette = schematic.get_region(0).get_palette()
            source_blocks = schematic.get_region(0).get_blocks()
            source_entities = schematic.get_region(0).get_entities()
            
        (width, height, length) = schematic.get_region(0).get_size()
        pos1, _ = schematic.get_region(0).get_bounding_box()
        
        requiredMods = []
                
        if BlockState.AIR_BLOCK in source_palette:
            air_block = source_palette.index(BlockState.AIR_BLOCK)
        else:
            air_block = 0
            source_palette.insert(0, BlockState.AIR_BLOCK)
        
        blocks = {}
        for block in source_blocks:
            modId, _, _ = block.state.Name.partition(":")
            if modId != "minecraft" and modId not in requiredMods:
                requiredMods.append(modId)
            
            if block.state not in source_palette:
                source_palette.append(block.state)
                
            i = block.pos.x + block.pos.z * width + block.pos.y * length * width
            blocks[i] = source_palette.index(block.state)
            
        metadata = {}
        if name := schematic.get_name():
            metadata["Name"] = name
        if author := schematic.get_metadata().get("author"):
            metadata["Author"] = author
        if date := schematic.get_metadata().get("date"):
            metadata["Date"] = date
        if requiredMods:
            metadata["RequiredMods"] = requiredMods
        
        return cls.model_validate({
            "Version": 1,
            "Metadata": metadata,
            "Width": width,
            "Height": height,
            "Length": length,
            "Offset": [pos1.x, pos1.y, pos1.z],
            "Palette": {p.to_string(): i for (i, p) in enumerate(source_palette)},
            "PaletteMax": len(source_palette),
            "BlockData": [blocks[i] if i in blocks else air_block for i in range(width * height * length)],
            "TileEntities": source_entities
        })
        
    def schematic_dump(self):
        as_nbt = nbt.model_to_compound(self, "Schematic")
        return as_nbt.to_bytes(True)
    
    def get_minecraft_version(self):
        # TODO: This is totally not a safe guess
        return self.get_translation_manager().get_version("java", (1, 13, 2))