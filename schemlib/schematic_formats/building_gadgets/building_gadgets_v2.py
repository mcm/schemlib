import base64
from typing import Annotated, Any, ClassVar, Optional, Self, cast

from pydantic import BaseModel, field_serializer, field_validator
from PyMCTranslate import Version

from schemlib import nbt, snbt
from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic
from schemlib.schematic_formats.building_gadgets.common import BGBlockPos


class BuildingGadgetsV2StatePosArrayList(BaseModel):
    blockstatemap: nbt.List[BlockState]
    startpos: BGBlockPos
    endpos: BGBlockPos
    statelist: nbt.IntArray

    @field_validator("blockstatemap", mode="plain")
    @classmethod
    def preserve_blockstatemap_as_nbt(cls, value):
        return nbt.List([BlockState.model_validate(x) for x in value])


class BuildingGadgetsV2Schematic(BaseModel, AbstractRegion, AbstractSchematic):
    MAX_WIDTH: ClassVar[int] = 500
    MAX_HEIGHT: ClassVar[int] = 500
    MAX_LENGTH: ClassVar[int] = 500
    MAX_TOTAL_VOLUME: ClassVar[int] = 100000

    name: str
    statePosArrayList: "BuildingGadgetsV2StatePosArrayList"
    requiredItems: dict[str, int]

    @field_validator("statePosArrayList", mode="before")
    @classmethod
    def decode(cls, value: str) -> Any:
        if not isinstance(value, str):
            return value
        return snbt.from_snbt(value)
        
    @field_serializer("statePosArrayList", mode="plain", when_used="json")
    def serialize_state_pos_array_list(self, value) -> str:
        nbt_value = nbt.model_to_compound(value, name="")
        return snbt.to_snbt(nbt_value)

    @classmethod
    def get_format_description(cls) -> str:
        return "Building Gadgets 2 (Minecraft 1.20+) Template"

    @classmethod
    def get_default_extension(cls):
        return "txt"

    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 20, 1))

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        return cls.model_validate_json(obj)

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        palette: list[BlockState] = self.statePosArrayList.blockstatemap
        (width, height, length) = self.get_size()

        blocks = {}
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    i = x + y * width + z * height * width

                    stateidx = cast(int, self.statePosArrayList.statelist[i])
                    blocks[(x, y, z)] = Block(pos=BlockPos(x=x, y=y, z=z), state=palette[stateidx])
        return blocks
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {}
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {}

    def get_bounding_box(self) -> tuple[BlockPos, BlockPos]:
        return (self.statePosArrayList.startpos, self.statePosArrayList.endpos)

    def get_origin(self) -> BlockPos:
        return self.statePosArrayList.startpos

    # def get_palette(self) -> list[BlockState]:
    #     blockstatemap = self.statePosArrayList.blockstatemap
    #     return cast(list[BlockState], blockstatemap)

    def get_size(self) -> tuple[int, int, int]:
        dim = self.statePosArrayList.endpos - self.statePosArrayList.startpos
        return (abs(dim.x) + 1, abs(dim.y) + 1, abs(dim.z) + 1)

    def get_metadata(self):
        return {}

    def get_name(self) -> str:
        return self.name or "unknown building gadgets v2 schematic"
    
    def get_regions(self) -> list[AbstractRegion]:
        return [self]
        # return [
        #     BuildingGadgetsV2Region(
        #         statePosArrayList=self.statePosArrayList
        #     )
        # ]

    @classmethod
    def check_size(cls, width: int, height: int, length: int):
        if width > cls.MAX_WIDTH:
            msg = f"Width axis too big, {width} > {cls.MAX_WIDTH}"
            raise ValueError(msg)
        if height > cls.MAX_HEIGHT:
            msg = f"Height axis too big, {height} > {cls.MAX_HEIGHT}"
            raise ValueError(msg)
        if length > cls.MAX_LENGTH:
            msg = f"Length axis too big, {length} > {cls.MAX_LENGTH}"
            raise ValueError(msg)

        volume = width * height * length
        if volume > cls.MAX_TOTAL_VOLUME:
            msg = f"Total schematic area too big, {volume} > {cls.MAX_TOTAL_VOLUME}"
            raise ValueError(msg)

    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]) -> Self:
        if len(schematic.get_regions()) > 1:  # pragma: nocover
            msg = f"Too many regions in source schematic ({len(schematic.get_regions())})"
            raise ValueError(msg)
        
        pos1, pos2 = schematic.get_region(0).get_bounding_box()

        (width, height, length) = schematic.get_region(0).get_size()
        cls.check_size(width, height, length)

        statelist: dict[int, int] = {}
        required_items: dict[str, int] = {}
        
        if target_version is not None and target_version != schematic.get_minecraft_version():
            blocks = schematic.get_region(0).get_translated_blocks(target_version)
            palette = schematic.get_region(0).get_translated_palette(target_version)
        else:
            blocks = schematic.get_region(0).get_blocks()
            palette = schematic.get_region(0).get_palette()

        if BlockState.AIR_BLOCK in palette:
            air_block = palette.index(BlockState.AIR_BLOCK)
        else:
            air_block = 0
            palette.insert(0, BlockState.AIR_BLOCK)
        
        for block in blocks:
            i = block.pos.x + block.pos.y * width + block.pos.z * (width * height)
            statelist[i] = palette.index(block.state)

            if block.state.Name not in required_items:
                required_items[block.state.Name] = 0
            required_items[block.state.Name] += 1

        return cls.model_validate(
            {
                "name": schematic.get_name(),
                "statePosArrayList": {
                    "blockstatemap": palette,
                    "startpos": BlockPos.ORIGIN,
                    "endpos": pos2 - pos1,
                    "statelist": [statelist[i] if i in statelist else air_block for i in range(width * height * length)],
                },
                "requiredItems": required_items,
            }
        )

    def schematic_dump(self):
        return self.model_dump_json()

    def get_minecraft_version(self):
        return self.get_translation_manager().get_version("java", (1, 20, 1))
