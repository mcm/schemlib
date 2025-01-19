import gzip
import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Self, cast

from PyMCTranslate import TranslationManager, Version, new_translation_manager
from PyMCTranslate.py3.api.amulet_objects.block import Block as AmuletBlock
from quarry.types import nbt

from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats.version_mapping import MinecraftVersionMapper
# from schemlib.snbt import from_snbt

__all__ = [
    "AbstractRegion",
    "AbstractSchematic",
    # "get_schematic_type",
]


class AbstractRegion(ABC):
    # @abstractmethod
    # def get_size(self) -> tuple[int, int, int]: ...

    @abstractmethod
    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]: ...
    
    @abstractmethod
    def get_minecraft_version(self) -> Version: ...

    @abstractmethod
    def get_origin(self) -> BlockPos: ...
    
    @abstractmethod
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]: ...
    
    @abstractmethod
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]: ...

    # TODO: Add biome support
    # @abstractmethod
    # def get_biomes(self) -> list[Biome]:
    #     return []

    # TODO: Add entity support
    # @abstractmethod
    # def get_entities(self) -> list[Entity]:
    #     return []
    
    def get_blocks(self) -> list[Block]:
        return list(self.get_block_matrix().values())
    
    def get_entities(self) -> list[Entity]:
        return list(self.get_entity_matrix().values())
    
    def get_tile_entities(self) -> list[Entity]:
        return list(self.get_tile_entity_matrix().values())

    def get_bounding_box(self) -> tuple[BlockPos, BlockPos]:
        p0, p1 = None, None
        
        for block in self.get_blocks():
            block_pos = block.pos.astuple()
            if p0 is None:
                p0 = block_pos
            else:
                p0 = tuple(min(a, b) for (a, b) in zip(p0, block_pos))
                
            if p1 is None:
                p1 = block_pos
            else:
                p1 = tuple(max(a, b) for (a, b) in zip(p1, block_pos))
                
        if p0 is None or p1 is None:
            return (BlockPos.ORIGIN, BlockPos.ORIGIN)
                
        return (BlockPos(x=p0[0], y=p0[1], z=p0[2]), BlockPos(x=p1[0], y=p1[1], z=p1[2]))

    def get_palette(self) -> list[BlockState]:
        return list({b.state for b in self.get_blocks()})
    
    def get_size(self) -> tuple[int, int, int]:
        if len(self.get_blocks()) == 0:
            return (0, 0, 0)
        
        p0, p1 = self.get_bounding_box()
        return (
            abs(p1[0] - p0[0]) + 1,
            abs(p1[1] - p0[1]) + 1,
            abs(p1[2] - p0[2]) + 1,
        )
    
    def get_translated_blocks(self, target_version: Version) -> list[Block]:
        mapper = MinecraftVersionMapper(self.get_block_matrix(), self.get_minecraft_version())
        return [mapper.map_block(block, target_version) for block in self.get_blocks()]
    
    def get_translated_block_matrix(self, target_version: Version) -> dict[tuple[int, int, int], Block]:
        mapper = MinecraftVersionMapper(self.get_block_matrix(), self.get_minecraft_version())
        return {pos: mapper.map_block(block, target_version) for (pos, block) in self.get_block_matrix().items()}
    
    def get_translated_entities(self, target_version: Version) -> list[Entity]:
        return self.get_entities()
    
    def get_translated_entity_matrix(self, target_version: Version) -> dict[tuple[float, float, float], Entity]:
        return self.get_entity_matrix()
    
    def get_translated_tile_entities(self, target_version: Version) -> list[Entity]:
        return self.get_tile_entities()
    
    def get_translated_tile_entity_matrix(self, target_version: Version) -> dict[tuple[int, int, int], Entity]:
        return self.get_tile_entity_matrix()
    
    def get_translated_palette(self, target_version: Version) -> list[BlockState]:
        return list({b.state for b in self.get_translated_blocks(target_version)})


class AbstractSchematic(ABC):
    _translation_manager: TranslationManager | None = None

    @classmethod
    @abstractmethod
    def get_format_description(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_default_extension(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_default_version(cls) -> Version: ...

    @classmethod
    @abstractmethod
    def schematic_load(cls, obj: str | bytes) -> Self: ...

    @classmethod
    @abstractmethod
    def from_schematic(cls, schematic: "AbstractSchematic", target_version: Optional[Version]) -> Self: ...

    @abstractmethod
    def get_metadata(self) -> Any: ...

    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def schematic_dump(self) -> str | bytes: ...

    @abstractmethod
    def get_minecraft_version(self) -> Version: ...
    
    @abstractmethod
    def get_regions(self) -> list[AbstractRegion]: ...
    
    def get_region(self, idx: int) -> AbstractRegion:
        return self.get_regions()[idx]

    @classmethod
    def check_size(cls, width: int, height: int, length: int):
        pass

    @classmethod
    def get_translation_manager(cls):
        if cls._translation_manager is None:
            cls._translation_manager = new_translation_manager()
        return cls._translation_manager

    # @classmethod
    # def translate_version(cls, schematic: "AbstractSchematic", version: str | Version, blockMapping: Optional[dict[str, str]] = None) -> Self:
    #     # Create an intermediate GenericSchematic with the translated values
    #     # Then create an instance of cls from that
    #     if isinstance(version, str):
    #         version = new_translation_manager().get_version("java", [int(x) for x in version.split(".")])

    #     intermediate = IntermediateSchematic.from_schematic(schematic)
    #     if blockMapping:
    #         intermediate.map_blocks(blockMapping)
    #     intermediate.translate_blocks(version)
    #     return cls.from_schematic(intermediate)
    
    
# def get_schematic_type(v):
#     def check(o, k):
#         if isinstance(o, dict):
#             return k in o
#         if isinstance(o, nbt.TagCompound):
#             return k in o.to_obj()
#         return hasattr(o, k)

#     if isinstance(v, (str, bytes)):
#         try:
#             v = json.loads(v)
#         except:
#             try:
#                 v = nbt.TagRoot.from_bytes(gzip.decompress(cast(bytes, v)))
#             except:
#                 try:
#                     v = from_snbt(cast(str, v))
#                 except:
#                     raise TypeError(v)
#             else:
#                 if isinstance(v, nbt.TagRoot):
#                     v = v.body if "" in v.value else nbt.TagCompound(v.value)

#     if check(v, "header"):
#         return "BuildingGadgets[1.14.4-1.19.3]"
#     elif check(v, "stateIntArray"):
#         return "BuildingGadgets[1.12]"
#     elif check(v, "statePosArrayList"):
#         return "BuildingGadgets2[1.20+]"

#     if check(v, "Regions"):
#         return "Litematic"

#     if check(v, "Schematic"):
#         if isinstance(v, dict):
#             v = v["Schematic"]
#         elif isinstance(v, nbt.TagCompound):
#             v = v.to_obj()["Schematic"]
#         else:
#             v = cast(Any, v).Schematic

#     if all([check(v, k) for k in ("Version", "Metadata", "Offset")]):
#         version = None
#         if isinstance(v, dict):
#             version = v["Version"]
#         elif isinstance(v, nbt.TagCompound):
#             version = v.to_obj().get("Version")
#         else:
#             version = cast(Any, v).Version

#         if version is None:
#             raise ValueError(version)

#         return f"Sponge[v{version}]"

#     if check(v, "blocks") and check(v, "DataVersion"):
#         return "Structure"

#     raise TypeError(v)