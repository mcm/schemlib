from dataclasses import dataclass
from typing import Annotated, Any, Optional, Self, cast

from PyMCTranslate import Version
from pydantic import BaseModel, field_validator, model_validator

from schemlib import nbt, snbt
from schemlib.blocks import BlockPos, Block, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic
from schemlib.schematic_formats.building_gadgets.common import BGBlockPos
# from schemlib.nbt_fields import LowerCaseKeysValidator, NBTBlockState, NBTCompound, NBTCompoundTransfomSerializer, NBTInt, NBTIntArray, NBTList, NBTShort
# from schemlib.nbt_models import NBTModel, SNBTModel


class BuildingGadgetsV0MapIntState(BaseModel):
    mapSlot: nbt.Short
    mapState: BlockState
    
    @field_validator("mapState", mode="plain")
    @classmethod
    def preserve_blockstate_as_nbt(cls, value):
        return value


class BuildingGadgetsV0Schematic(BaseModel, AbstractRegion, AbstractSchematic):
    stateIntArray: nbt.IntArray
    dim: nbt.Int
    posIntArray: nbt.IntArray
    startPos: BGBlockPos
    endPos: BGBlockPos
    mapIntState: nbt.List[BuildingGadgetsV0MapIntState]
    
    @field_validator("mapIntState", mode="plain")
    @classmethod
    def parse_map_int_state(cls, objList: nbt.List):
        return [BuildingGadgetsV0MapIntState.model_validate(item) for item in objList]
    
    @staticmethod
    def get_pos_for_int(pos_int) -> BlockPos:
        # x = (pos >> 16) & 0xFF
        x = (pos_int & 0xFF0000) >> 16
        if x & 0x80 != 0:
            x = x - 0x100

        # y = (pos >> 8) & 0xFF
        y = (pos_int & 0x00FF00) >> 8
        if y & 0x80 != 0:
            y = y - 0x100

        z = pos_int & 0xFF
        if z & 0x80 != 0:
            z = z - 0x100

        return BlockPos(
            x=x,
            y=y,
            z=z,
        )

    @classmethod
    def get_default_extension(cls) -> str:
        return "txt"

    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 12, 2))

    @classmethod
    def get_format_description(cls) -> str:
        return "Building Gadgets (Minecraft 1.12) Template"

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        if not isinstance(obj, str):
            string_value = cast(bytes, obj).decode("utf-8")
        else:
            string_value = obj
            
        return cls.model_validate(snbt.from_snbt(string_value))
        
    # def get_size(self) -> tuple[int, int, int]:
    #     return (
    #         abs(self.startPos.x - self.endPos.x) + 1,
    #         abs(self.startPos.y - self.endPos.y) + 1,
    #         abs(self.startPos.z - self.endPos.z) + 1,
    #     )

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        palette = {x.mapSlot: x.mapState for x in self.mapIntState}

        blocks = {}
        # (origin_x, origin_y, origin_z) = self.get_origin().astuple()
        
        block_positions = [self.get_pos_for_int(x) for x in self.posIntArray]
        offset_x = min([pos.x for pos in block_positions])
        offset_y = min([pos.y for pos in block_positions])
        offset_z = min([pos.z for pos in block_positions])

        for idx, pos_int in enumerate(self.posIntArray):
            pos = self.get_pos_for_int(pos_int) - (offset_x, offset_y, offset_z)

            stateidx: int = cast(int, self.stateIntArray[idx])
            state = palette[stateidx]

            # if state.Name == "minecraft:air":
            #     continue

            blocks[(pos.x, pos.y, pos.z)] = Block(pos=pos, state=state)

        return blocks
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {}
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {}

    # def get_bounding_box(self) -> tuple[BlockPos, BlockPos]:
    #     pos1 = self.get_origin()
    #     pos2 = (pos1 + self.get_size()) - BlockPos(x=1, y=1, z=1)
    #     return (pos1, pos2)

    def get_origin(self) -> BlockPos:
        return BlockPos(x=0, y=0, z=0)

    def get_metadata(self) -> Any:
        return {}

    def get_name(self) -> str:
        return "unknown 1.12 building gadgets template"
    
    def get_regions(self) -> list[AbstractRegion]:
        return [self]
        # return [
        #     BuildingGadgetsV0Region.model_validate(dict(
        #         startPos=self.startPos,
        #         endPos=self.endPos,
        #         stateIntArray=self.stateIntArray,
        #         posIntArray=self.posIntArray,
        #         mapIntState=self.mapIntState,
        #     ))
        # ]

    def get_minecraft_version(self) -> Version:
        return self.get_translation_manager().get_version("java", (1, 12, 2))

    def schematic_dump(self) -> str | bytes:
        # return self.model_dump(context=NBTModelSerializationContext(mode="snbt"))
        return snbt.to_snbt(nbt.model_to_compound(self))

    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]) -> Self:  # pragma: nocover
        raise NotImplementedError
