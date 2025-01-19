import gzip
import struct
from collections.abc import Sequence
from functools import partial
from math import ceil, log2
from types import GenericAlias, new_class
from typing import Annotated, Any, Literal, Optional, Protocol, TYPE_CHECKING, cast, overload, runtime_checkable

from bitstring import Array, BitArray, BitStream, Bits, Dtype
from bitstring.bits import BitsType
from pydantic import BaseModel, GetCoreSchemaHandler, SerializationInfo, TypeAdapter
from pydantic_core import core_schema


__all__ = [
    "Byte",
    "Short",
    "Int",
    "Long",
    "Float",
    "Double",
    "ByteArray",
    "String",
    "List",
    "Compound",
    "IntArray",
    "LongArray",
    "AnyNBT",
    "ArrayTag",
    "model_to_compound",
    "load_nbt_from_bytes",
    "load_nbt_from_file",
]


tag_type_registry: dict[int, type["NbtTag"]] = {}


@overload
def register_tag_type(tag_type_id: int, tag_type: type["NbtTag"], *, overwrite: bool) -> type["NbtTag"]: ...

@overload
def register_tag_type(tag_type_id: int, tag_type: type["NbtTag"]) -> type["NbtTag"]: ...

@overload
def register_tag_type(tag_type_id: int, *, overwrite: bool) -> partial: ...

@overload
def register_tag_type(tag_type_id: int) -> partial: ...

def register_tag_type(tag_type_id: int, tag_type: Optional[type["NbtTag"]]=None, *, overwrite: bool=False):
    if tag_type is None:
        return partial(register_tag_type, tag_type_id, overwrite=overwrite)
    
    if not issubclass(tag_type, NbtTag):
        raise TypeError(type(tag_type))
    
    if tag_type_id in tag_type_registry and not overwrite:
        existing_tag_type = tag_type_registry[tag_type_id]
        msg = f"{existing_tag_type.__name__} already registered for id {tag_type_id}"
        raise KeyError(msg)
    tag_type_registry[tag_type_id] = tag_type
    tag_type.tag_type_id = tag_type_id
    return tag_type


class NbtTag[T: type]:
    tag_type_id: int
    __python_type__: T
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        json_schema = core_schema.chain_schema(
            [
                # handler(cls.__python_type__),
                core_schema.no_info_plain_validator_function(cls),
                # core_schema.no_info_plain_validator_function(validate)
            ]
        )
        python_schema = core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
                json_schema
            ]
        )
        
        return core_schema.json_or_python_schema(
            json_schema=json_schema,
            python_schema=python_schema,
            # serialization=core_schema.plain_serializer_function_ser_schema(lambda tag: tag.to_obj()),
            # serialization=core_schema.wrap_serializer_function_ser_schema(serialize)
        )
        
    @classmethod
    def from_bytes(cls, bytes_: bytes):
        return cls.from_buff(BitStream(bytes_))
        
    @classmethod
    def from_buff(cls, buff: BitStream):
        raise NotImplementedError

    def to_bytes(self):
        raise NotImplementedError
    
    def __eq__(self, other):
        return self.to_obj() == other
    
    def __hash__(self):
        return self.__python_type__(self).__hash__()
        
    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__python_type__(self))

    @classmethod
    def nbt_tag_class_factory(cls, python_type: T) -> T:
        nbt_tag_cls = new_class(
            f"{NbtTag}[{python_type.__name__}]",
            (GenericAlias(cls, (python_type,)), python_type),
            {},
            lambda ns: ns.update({"__python_type__": python_type})
        )
        return cast(T, nbt_tag_cls)
    
    def to_obj(self):
        return self.__python_type__(self)


class _DataTag[T: type[int | float]](NbtTag[T]):
    fmt: str

    @classmethod
    def from_buff(cls, buff: BitStream):
        value = buff.read(cls.fmt)
        return cls(value)  # type: ignore

    def to_bytes(self) -> bytes:
        return Dtype(self.fmt).build(self).tobytes()
        # return struct.pack(self.fmt, self)


@register_tag_type(1)
class Byte(_DataTag.nbt_tag_class_factory(int)):
    fmt = "intbe8"
    
@register_tag_type(2)
class Short(_DataTag.nbt_tag_class_factory(int)):
    fmt = "intbe16"
    
@register_tag_type(3)
class Int(_DataTag.nbt_tag_class_factory(int)):
    fmt = "intbe32"

@register_tag_type(4)
class Long(_DataTag.nbt_tag_class_factory(int)):
    fmt = "intbe64"

@register_tag_type(5)
class Float(_DataTag.nbt_tag_class_factory(float)):
    fmt = "floatbe32"

@register_tag_type(6)
class Double(_DataTag.nbt_tag_class_factory(float)):
    fmt = "floatbe64"
    
    
class _ArrayTag(NbtTag.nbt_tag_class_factory(Sequence[int])):
    _storage: BitArray
    width: Dtype
    virtual_width: Optional[Dtype] = None
    
    def __init__(self, values: Array | BitsType | None):
        if isinstance(values, BitArray):
            self._storage = values
        elif isinstance(values, Array):
            self._storage = values.data
        else:
            self._storage = Array(self.width, values).data
            
    @classmethod
    def calcsize(cls, values: int | list[int]):
        if isinstance(values, int):
            values = [values]
        size = max(ceil(log2(max(map(abs, values)))), 2)
        if any((x < 0 for x in values)):
            size += 1
        return size
    
    @classmethod
    def empty(cls, length: int):
        return cls([0] * length)

    @classmethod
    def from_buff(cls, buff: BitStream):
        length = buff.read("uintbe32")
        data = buff.read(length * cls.width.bitlength)
        return cls(data)
            
    @classmethod
    def pack_list(cls, values: list[int], width: Optional[int]=None):
        if cls.width.bitlength is None:
            msg = f"Width {cls.width} has a variable bitlength"
            raise ValueError(msg)
        
        if width is None:
            width = max(2, ceil(log2(max(values))))
            
        length = ceil((len(values) * width) / cls.width.bitlength)
            
        obj = cls.empty(length)
        view = obj(width)
        for (i, value) in enumerate(values):
            view[i] = value
        return obj
            
        # a = Array(Dtype("uint", width), values)
        # needs_padding = len(a.data) % cls.width.bitlength
        # if needs_padding > 0:
        #     a.data.prepend(Bits(uint=0, length=cls.width.bitlength - needs_padding))

        # return cls(a)        
        # return cls(Array(Dtype("uint", width), values))
        
    def asarray(self, dtype: int | str | Dtype | None=None):
        if dtype is None:
            return Array(self.width, self._storage)
        if isinstance(dtype, str):
            dtype = Dtype(dtype)
        elif isinstance(dtype, int):
            dtype = Dtype("uint", dtype)
            
        return Array(dtype, self._storage)

    def to_bytes(self) -> bytes:
        if self.width.bitlength is None:
            msg = f"Width {self.width} has a variable bitlength"
            raise ValueError(msg)
        
        # Create a copy
        data = self._storage[:]
        needs_padding = len(data) % self.width.bitlength
        if needs_padding > 0:
            data.prepend(Bits(uint=0, length=self.width.bitlength - needs_padding))
        arr = Array(self.width, data)
        
        buff = BitStream()
        buff += Bits(uintbe32=len(arr))
        buff += arr.tobytes()
        return buff.tobytes()
    
    def to_obj(self):
        return self.asarray().tolist()
    
    def __len__(self):
        return len(Array(self.width, self._storage))
    
    def __iter__(self):
        return iter(self.asarray())
    
    def __getitem__(self, idx) -> int:
        if self.virtual_width is None:
            return self.asarray()[idx]
            
        if self.width.bitlength is None:
            msg = f"Width {self.width} has a variable bitlength"
            raise ValueError(msg)
            
        if self.virtual_width.bitlength is None:
            msg = f"Width {self.virtual_width} has a variable bitlength"
            raise ValueError(msg)
        
        arr = Array(self.width)
        arr.data = self._storage
        
        start_offset = idx * self.virtual_width.bitlength
        start_arr_index = start_offset // self.width.bitlength
        end_arr_index = ((idx + 1) * self.virtual_width.bitlength - 1) // self.width.bitlength
        start_bit_offset = start_offset % self.width.bitlength
        
        if start_arr_index == end_arr_index:
            val = arr[start_arr_index] >> start_bit_offset
        else:
            end_offset = self.width.bitlength - start_bit_offset
            val = arr[start_arr_index] >> start_bit_offset | arr[end_arr_index] << end_offset
            
        return val & ((1 << self.virtual_width.bitlength) - 1)
    
    def __setitem__(self, idx, value):
        if self.virtual_width is None:
            bits = self.width.build(value)
            self._storage.overwrite(bits, idx * self.width.bitlength)
            return
            
        if self.width.bitlength is None:
            msg = f"Width {self.width} has a variable bitlength"
            raise ValueError(msg)
            
        if self.virtual_width.bitlength is None:
            msg = f"Width {self.virtual_width} has a variable bitlength"
            raise ValueError(msg)
        
        start_offset = idx * self.virtual_width.bitlength
        start_arr_index = start_offset // self.width.bitlength
        end_arr_index = ((idx + 1) * self.virtual_width.bitlength - 1) // self.width.bitlength
        start_bit_offset = start_offset % self.width.bitlength
        
        arr = Array(self.width)
        arr.data = self._storage
        
        m = (1 << self.width.bitlength) - 1
        mask = (1 << self.virtual_width.bitlength) - 1
        
        zeroed = arr[start_arr_index] & ~(mask << start_bit_offset)
        updated = zeroed | (value & mask) << start_bit_offset
        arr[start_arr_index] = updated & m

        if start_arr_index != end_arr_index:
            end_offset = 64 - start_bit_offset
            j1 = self.virtual_width.bitlength - end_offset
            arr[end_arr_index] = (arr[end_arr_index] >> j1 << j1 | (
                    value & mask) >> end_offset) & m
            
    def __eq__(self, other) -> bool:
        return self.asarray() == other
    
    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, list(self))
    
    def __call__(self, dtype: int | str | Dtype, length: Optional[int]=None):
        if isinstance(dtype, str):
            dtype = Dtype(dtype)
        elif isinstance(dtype, int):
            dtype = Dtype("uint", dtype)
            
        if dtype.bitlength is None:
            msg = f"Width {dtype} has a variable bitlength"
            raise ValueError(msg)
        
        cls = new_class(
            "ArrayView",
            (self.__class__,),
            {},
            lambda ns: ns.update({"virtual_width": dtype})
        )
        
        return cls(self._storage)


@register_tag_type(7)
class ByteArray(_ArrayTag):
    width = Dtype("uint8")

@register_tag_type(11)
class IntArray(_ArrayTag):
    width = Dtype("uint32")

@register_tag_type(12)
class LongArray(_ArrayTag):
    width = Dtype("uint64")


@register_tag_type(8)
class String(NbtTag.nbt_tag_class_factory(str)):
    @classmethod
    def from_buff(cls, buff: BitStream):
        string_length = buff.read("uintbe16")
        val = cls(buff.read(string_length * 8).tobytes().decode("utf8"))
        return val
    
    def to_bytes(self):
        buff = BitStream()
        buff += Bits(uintbe16=len(self))
        buff += str(self).encode("utf8")
        return buff.tobytes()
        
    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__python_type__(self))
    

@register_tag_type(9)
class List[T](NbtTag.nbt_tag_class_factory(list[T])):
    @classmethod
    def from_buff(cls, buff: BitStream):
        item_tag_type_id, list_length = cast(list[int], buff.readlist(["intbe8", "intbe32"]))
        if item_tag_type_id == 0:
            return cls([])
        elif item_tag_type_id not in tag_type_registry:
            msg = f"No tag class registered for id {item_tag_type_id}"
            raise ValueError(msg)
        else:
            item_tag_type = tag_type_registry[item_tag_type_id]
        return cls([item_tag_type.from_buff(buff) for _ in range(list_length)])
    
    def to_bytes(self) -> bytes:
        if len(self) > 0:
            item_tag_type_id = self[0].tag_type_id
        else:
            item_tag_type_id = 0
        packed = BitStream(Dtype("uintbe8").build(item_tag_type_id) + Dtype("uintbe32").build(len(self)))
        for item in self:
            packed += item.to_bytes()
        return packed.tobytes()
    
    def to_obj(self):
        result = []
        for item in self:
            if isinstance(item, BaseModel):
                item = model_to_compound(item)
            result.append(item.to_obj())
        return result


@register_tag_type(10)
class Compound[T](NbtTag.nbt_tag_class_factory(dict[str, T])):
    @classmethod
    def from_buff(cls, buff: BitStream):
        data = {}
        while True:
            if buff.pos == len(buff):
                break
            tag_type_id = buff.read("intbe8")
            if tag_type_id == 0:
                break
            if tag_type_id not in tag_type_registry:
                msg = f"No tag class registered for id {tag_type_id}"
                raise ValueError(msg)
            tag_type = tag_type_registry[tag_type_id]
            key = String.from_buff(buff).to_obj()
            data[key] = tag_type.from_buff(buff)
            
        return cls(data)
    
    def to_bytes(self) -> bytes:
        buff = BitStream()

        for key, value in cast(list[tuple[str, NbtTag]], self.items()):
            print(key, type(value))
            buff += Dtype("intbe8").build(value.tag_type_id)
            buff += String(key).to_bytes()
            buff += value.to_bytes()
            
        buff += Dtype("intbe8").build(0)
        
        return buff.tobytes()
    
    def to_obj(self):
        return {k: v.to_obj() if isinstance(v, NbtTag) else v for (k, v) in self.items()}
            

class Named(Compound[Compound]):
    name: str
    
    def __init__(self, initialdata, /, **kwargs):
        initialdata.update(**kwargs)
        if len(initialdata.keys()) > 1:
            msg = f"Named tag can only have one key, but got {len(initialdata.keys())}"
            raise ValueError(msg)
        self.name, = initialdata.keys()
        super().__init__(initialdata[self.name])
        
    def to_bytes(self, compress=False) -> bytes:
        buff = BitStream()
        buff += Dtype("uintbe8").build(Compound.tag_type_id)
        buff += String(self.name).to_bytes()
        buff += super().to_bytes()
        
        bytes_ = buff.tobytes()
        if compress:
            return gzip.compress(bytes_, mtime=0)
        return bytes_
        
    def to_obj(self):
        return {self.name: dict(self)}
        
    def __repr__(self):
        return "%s({'%s': %s})" % (type(self).__name__, self.name, Compound(self))
    
    
AnyNBT = Byte | Short | Int | Long | Float | Double | String | List | Compound | Named
ArrayTag = ByteArray | IntArray | LongArray


@runtime_checkable
class HasModelDumpNbt(Protocol):
    def model_dump_nbt(self, name: Optional[str]=None): ...
    
    
@overload
def model_to_compound(instance: BaseModel) -> Compound[dict]: ...

@overload
def model_to_compound(instance: BaseModel, name: Literal[None]) -> Compound[dict]: ...

@overload
def model_to_compound(instance: BaseModel, name: str) -> Named: ...

def model_to_compound(instance: BaseModel, name: Optional[str]=None):
    if isinstance(instance, HasModelDumpNbt):
        return instance.model_dump_nbt(name)
    
    as_dict = {}
    for field, value in instance:
        if isinstance(instance, BaseModel) and instance.model_fields[field].metadata:
            field_info = instance.model_fields[field]
            ta = TypeAdapter(Annotated[field_info.annotation, *field_info.metadata])
            as_dict[field] = ta.dump_python(value, serialize_as_any=True)
        elif isinstance(instance, BaseModel) and getattr(instance.model_fields[field].annotation, "_name", None) == "Optional" and value is None:
            continue
        elif isinstance(value, BaseModel):
            as_dict[field] = model_to_compound(value)
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], BaseModel):
            as_dict[field] = List([model_to_compound(x) for x in value])
        elif isinstance(value, Compound):
            as_dict[field] = Compound({k: model_to_compound(v) if isinstance(v, BaseModel) else v for (k, v) in value.items()})
        else:
            as_dict[field] = value
            
    if name is not None:
        return Named({name: as_dict})
    return Compound(as_dict)
    
    
@overload
def load_nbt_from_bytes(bytes_: bytes) -> Named: ...

@overload
def load_nbt_from_bytes(bytes_: bytes, model: Literal[None]) -> Named: ...

@overload
def load_nbt_from_bytes[T: BaseModel](bytes_: bytes, model: type[T]) -> T: ...

def load_nbt_from_bytes[T: BaseModel](bytes_: bytes, model: Optional[type[T]]=None):
    if bytes_[:2] == b"\x1f\x8b":
        bytes_ = gzip.decompress(bytes_)
    
    root_tag = Named.from_bytes(bytes_)
        
    if model is None:
        return root_tag
    
    return model.model_validate(root_tag)
    
    
@overload
def load_nbt_from_file(filepath: str) -> Named: ...

@overload
def load_nbt_from_file(filepath: str, model: Literal[None]) -> Named: ...

@overload
def load_nbt_from_file[T: BaseModel](filepath: str, model: type[T]) -> T: ...

def load_nbt_from_file[T: BaseModel](filepath: str, model: Optional[type[T]]=None):
    with gzip.open(filepath, "rb") as f:
        return load_nbt_from_bytes(f.read(), model)