import base64
from typing import Any, ClassVar, Optional, Self

from pydantic import BaseModel, field_serializer, field_validator
from PyMCTranslate import Version

from schemlib import nbt
from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic


class BoundingBox(BaseModel):
    min_x: int
    min_y: int
    min_z: int
    max_x: int
    max_y: int
    max_z: int
    

class BlockData(BaseModel):
    data: nbt.Compound
    state: BlockState
    serializer: nbt.Int
    
    @field_validator("data", mode="wrap")
    @classmethod
    def preserve_block_data_as_nbt(cls, value, handler):
        if isinstance(value, nbt.Compound):
            return value
        return handler(value)


class BuildingGadgetsV1Schematic(BaseModel, AbstractRegion, AbstractSchematic):
    MAX_WIDTH: ClassVar[int] = 65535
    MAX_HEIGHT: ClassVar[int] = 255
    MAX_LENGTH: ClassVar[int] = 65535

    header: "BuildingGadgetsV1SchematicHeader"
    body: "BuildingGadgetsV1SchematicBody"

    @field_validator("body", mode="before")
    @classmethod
    def decode(cls, value: str) -> Any:
        if not isinstance(value, str | bytes):
            return value
        body = base64.b64decode(value)
        return nbt.load_nbt_from_bytes(body)
        
    @field_serializer("body", mode="plain", when_used="json")
    def serialize_nbt_body(self, value) -> str:
        nbt_value = nbt.model_to_compound(value, name="")
        bytes_ = nbt_value.to_bytes(compress=True)
        return base64.b64encode(bytes_).decode()

    class BuildingGadgetsV1SchematicHeader(BaseModel):
        version: str
        mc_version: str
        name: str
        author: Optional[str] = None
        bounding_box: "BoundingBox"
        material_list: "MaterialList"

        class MaterialList(BaseModel):
            root_type: str
            root_entry: list["MaterialListEntry"]

            class MaterialListEntry(BaseModel):
                item_type: str
                count: int
                item: dict[str, str]

    class BuildingGadgetsV1SchematicBody(BaseModel):
        data: nbt.List["BlockData"]
        pos: nbt.List[nbt.Long]
        header: "Header"
        serializer: nbt.List[nbt.String]
    
        @field_validator("data", mode="plain")
        @classmethod
        def parse_data_as_list(cls, value):
            return nbt.List([BlockData.model_validate(x) for x in value])

        class Header(BaseModel):
            author: Optional[nbt.String] = None
            bounds: "Bounds"
            name: nbt.String

            class Bounds(BaseModel):
                minX: nbt.Int
                minY: nbt.Int
                minZ: nbt.Int
                maxX: nbt.Int
                maxY: nbt.Int
                maxZ: nbt.Int

    @staticmethod
    def parse_block_pos(v: int) -> tuple[BlockPos, int]:
        x = v >> 24 & 0xFFFF
        y = v >> 16 & 0xFF
        z = v & 0xFFFF
        state = v >> 40 & 0xFFFFFF

        return BlockPos(x=x, y=y, z=z), state

    @staticmethod
    def unparse_block_pos(pos: BlockPos, state: int) -> int:
        v = (state & 0xFFFFFF) << 40
        v |= (pos.x & 0xFFFF) << 24
        v |= (pos.y & 0xFF) << 16
        v |= pos.z & 0xFFFF
        return v

    @classmethod
    def get_format_description(cls) -> str:
        return "Building Gadgets (Minecraft 1.14-1.19) Template"

    @classmethod
    def get_default_extension(cls):
        return "txt"

    @classmethod
    def get_default_version(cls) -> Version:
        return cls.get_translation_manager().get_version("java", (1, 17, 1))

    @classmethod
    def schematic_load(cls, obj: str | bytes) -> Self:
        return cls.model_validate_json(obj)

    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        palette = [data.state for data in self.body.data]

        blocks = {}
        for pos_long in self.body.pos:
            pos, stateidx = self.parse_block_pos(pos_long)
            blocks[pos.astuple()] = Block(pos=pos, state=palette[stateidx])
        return blocks
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        return {}
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        return {}

    def get_bounding_box(self) -> tuple[BlockPos, BlockPos]:
        pos1 = BlockPos(
            x=self.header.bounding_box.min_x,
            y=self.header.bounding_box.min_y,
            z=self.header.bounding_box.min_z,
        )

        pos2 = BlockPos(
            x=self.header.bounding_box.max_x,
            y=self.header.bounding_box.max_y,
            z=self.header.bounding_box.max_z,
        )

        return (pos1, pos2)

    def get_origin(self) -> BlockPos:
        return BlockPos(
            x=self.header.bounding_box.min_x,
            y=self.header.bounding_box.min_y,
            z=self.header.bounding_box.min_z,
        )

    def get_size(self) -> tuple[int, int, int]:
        return (
            self.header.bounding_box.max_x - self.header.bounding_box.min_x + 1,
            self.header.bounding_box.max_y - self.header.bounding_box.min_y + 1,
            self.header.bounding_box.max_z - self.header.bounding_box.min_z + 1,
        )
    
    def get_regions(self) -> list[AbstractRegion]:
        return [self]
        # return [
        #     BuildingGadgetsV1Region(
        #         pos=self.body.pos,
        #         data=self.body.data,
        #         bounding_box=self.header.bounding_box,
        #         minecraft_version=self.get_minecraft_version()
        #     )
        # ]

    def get_metadata(self) -> dict[str, Any]:
        return {"author": self.header.author, "name": self.header.name, "serializers": self.body.serializer}

    def get_name(self) -> str:
        return self.header.name or "unknown building gadgets v1 schematic"

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

    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]) -> Self:
        if len(schematic.get_regions()) > 1:  # pragma: nocover
            msg = f"Too many regions in source schematic ({len(schematic.get_regions())})"
            raise ValueError(msg)
        
        pos1, pos2 = schematic.get_region(0).get_bounding_box()
        metadata = schematic.get_metadata()

        serializers = metadata.get("serializers", ["buildinggadgets:dummy_serializer"])

        (width, height, length) = schematic.get_region(0).get_size()
        cls.check_size(width, height, length)

        blockdata = []
        pos = []
        
        if target_version is not None and target_version != schematic.get_minecraft_version():
            blocks = schematic.get_region(0).get_translated_blocks(target_version)
        else:
            blocks = schematic.get_region(0).get_blocks()
        
        for block in blocks:
            if block.state is BlockState.AIR_BLOCK:
                continue
            bd = {"data": {}, "state": block.state}
            if serializers:
                bd["serializer"] = nbt.Int(0)
            if block.state not in blockdata:
                blockdata.append(bd)
            pos.append(cls.unparse_block_pos(block.pos, blockdata.index(bd)))

        return cls.model_validate(
            {
                "header": {
                    "version": "1.17.1",
                    "mc_version": "1.17.1",
                    "name": schematic.get_name(),
                    "author": metadata.get("author", ""),
                    "material_list": {"root_type": "buildinggadgets:entries", "root_entry": []},
                    "bounding_box": {
                        "min_x": pos1.x,
                        "min_y": pos1.y,
                        "min_z": pos1.z,
                        "max_x": pos2.x,
                        "max_y": pos2.y,
                        "max_z": pos2.z,
                    },
                },
                "body": {
                    "data": blockdata,
                    "pos": nbt.List([nbt.Long(x) for x in pos]),
                    "header": {
                        "author": metadata.get("author", "uknown[converted by cfwiz]"),
                        "bounds": {
                            "minX": pos1.x,
                            "minY": pos1.y,
                            "minZ": pos1.z,
                            "maxX": pos2.x,
                            "maxY": pos2.y,
                            "maxZ": pos2.z,
                        },
                        "name": schematic.get_name(),
                    },
                    "serializer": nbt.List([nbt.String(x) for x in serializers]),
                },
            }
        )

    def schematic_dump(self):
        return self.model_dump_json()

    def get_minecraft_version(self) -> Version:
        version = [int(x) for x in self.header.mc_version.split(".")]
        return self.get_translation_manager().get_version("java", version)