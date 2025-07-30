from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[DataType]
    INT8: _ClassVar[DataType]
    INT16: _ClassVar[DataType]
    INT32: _ClassVar[DataType]
    INT64: _ClassVar[DataType]
    UINT8: _ClassVar[DataType]
    UINT16: _ClassVar[DataType]
    UINT32: _ClassVar[DataType]
    UINT64: _ClassVar[DataType]
    FLOAT: _ClassVar[DataType]
    DOUBLE: _ClassVar[DataType]
    BOOLEAN: _ClassVar[DataType]
    STRING: _ClassVar[DataType]
    DATETIME: _ClassVar[DataType]
    TEXT: _ClassVar[DataType]
    UUID_TYPE: _ClassVar[DataType]
    DATASET_TYPE: _ClassVar[DataType]
    BYTES: _ClassVar[DataType]
    FILE: _ClassVar[DataType]
    TEMPLATE_TYPE: _ClassVar[DataType]
    PROPERTYSET_TYPE: _ClassVar[DataType]
    PROPERTYSETLIST_TYPE: _ClassVar[DataType]
UNKNOWN: DataType
INT8: DataType
INT16: DataType
INT32: DataType
INT64: DataType
UINT8: DataType
UINT16: DataType
UINT32: DataType
UINT64: DataType
FLOAT: DataType
DOUBLE: DataType
BOOLEAN: DataType
STRING: DataType
DATETIME: DataType
TEXT: DataType
UUID_TYPE: DataType
DATASET_TYPE: DataType
BYTES: DataType
FILE: DataType
TEMPLATE_TYPE: DataType
PROPERTYSET_TYPE: DataType
PROPERTYSETLIST_TYPE: DataType

class Payload(_message.Message):
    __slots__ = ("timestamp", "metrics", "seq", "uuid", "body")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    metrics: _containers.RepeatedCompositeFieldContainer[Metric]
    seq: int
    uuid: str
    body: bytes
    def __init__(self, timestamp: _Optional[int] = ..., metrics: _Optional[_Iterable[_Union[Metric, _Mapping]]] = ..., seq: _Optional[int] = ..., uuid: _Optional[str] = ..., body: _Optional[bytes] = ...) -> None: ...

class Metric(_message.Message):
    __slots__ = ("name", "alias", "timestamp", "datatype", "is_historical", "is_transient", "is_null", "metadata", "properties", "int_value", "long_value", "float_value", "double_value", "boolean_value", "string_value", "bytes_value", "dataset_value", "template_value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    DATATYPE_FIELD_NUMBER: _ClassVar[int]
    IS_HISTORICAL_FIELD_NUMBER: _ClassVar[int]
    IS_TRANSIENT_FIELD_NUMBER: _ClassVar[int]
    IS_NULL_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LONG_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    BYTES_VALUE_FIELD_NUMBER: _ClassVar[int]
    DATASET_VALUE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    alias: int
    timestamp: int
    datatype: int
    is_historical: bool
    is_transient: bool
    is_null: bool
    metadata: MetaData
    properties: PropertySet
    int_value: int
    long_value: int
    float_value: float
    double_value: float
    boolean_value: bool
    string_value: str
    bytes_value: bytes
    dataset_value: DataSet
    template_value: Template
    def __init__(self, name: _Optional[str] = ..., alias: _Optional[int] = ..., timestamp: _Optional[int] = ..., datatype: _Optional[int] = ..., is_historical: bool = ..., is_transient: bool = ..., is_null: bool = ..., metadata: _Optional[_Union[MetaData, _Mapping]] = ..., properties: _Optional[_Union[PropertySet, _Mapping]] = ..., int_value: _Optional[int] = ..., long_value: _Optional[int] = ..., float_value: _Optional[float] = ..., double_value: _Optional[float] = ..., boolean_value: bool = ..., string_value: _Optional[str] = ..., bytes_value: _Optional[bytes] = ..., dataset_value: _Optional[_Union[DataSet, _Mapping]] = ..., template_value: _Optional[_Union[Template, _Mapping]] = ...) -> None: ...

class MetaData(_message.Message):
    __slots__ = ("is_multi_part", "content_type", "size", "seq", "file_name", "file_type", "md5", "description")
    IS_MULTI_PART_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_TYPE_FIELD_NUMBER: _ClassVar[int]
    MD5_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    is_multi_part: bool
    content_type: str
    size: int
    seq: int
    file_name: str
    file_type: str
    md5: str
    description: str
    def __init__(self, is_multi_part: bool = ..., content_type: _Optional[str] = ..., size: _Optional[int] = ..., seq: _Optional[int] = ..., file_name: _Optional[str] = ..., file_type: _Optional[str] = ..., md5: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class PropertySet(_message.Message):
    __slots__ = ("keys",)
    KEYS_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[Property]
    def __init__(self, keys: _Optional[_Iterable[_Union[Property, _Mapping]]] = ...) -> None: ...

class Property(_message.Message):
    __slots__ = ("key", "type", "int_value", "long_value", "float_value", "double_value", "boolean_value", "string_value", "propertyset_value", "propertysets_value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LONG_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTYSET_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROPERTYSETS_VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    type: int
    int_value: int
    long_value: int
    float_value: float
    double_value: float
    boolean_value: bool
    string_value: str
    propertyset_value: PropertySet
    propertysets_value: PropertySetList
    def __init__(self, key: _Optional[str] = ..., type: _Optional[int] = ..., int_value: _Optional[int] = ..., long_value: _Optional[int] = ..., float_value: _Optional[float] = ..., double_value: _Optional[float] = ..., boolean_value: bool = ..., string_value: _Optional[str] = ..., propertyset_value: _Optional[_Union[PropertySet, _Mapping]] = ..., propertysets_value: _Optional[_Union[PropertySetList, _Mapping]] = ...) -> None: ...

class PropertySetList(_message.Message):
    __slots__ = ("propertyset",)
    PROPERTYSET_FIELD_NUMBER: _ClassVar[int]
    propertyset: _containers.RepeatedCompositeFieldContainer[PropertySet]
    def __init__(self, propertyset: _Optional[_Iterable[_Union[PropertySet, _Mapping]]] = ...) -> None: ...

class DataSet(_message.Message):
    __slots__ = ("num_of_columns", "columns", "types", "rows")
    NUM_OF_COLUMNS_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    TYPES_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    num_of_columns: int
    columns: _containers.RepeatedScalarFieldContainer[str]
    types: _containers.RepeatedScalarFieldContainer[int]
    rows: _containers.RepeatedCompositeFieldContainer[Row]
    def __init__(self, num_of_columns: _Optional[int] = ..., columns: _Optional[_Iterable[str]] = ..., types: _Optional[_Iterable[int]] = ..., rows: _Optional[_Iterable[_Union[Row, _Mapping]]] = ...) -> None: ...

class Row(_message.Message):
    __slots__ = ("elements",)
    ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    elements: _containers.RepeatedCompositeFieldContainer[DataSetValue]
    def __init__(self, elements: _Optional[_Iterable[_Union[DataSetValue, _Mapping]]] = ...) -> None: ...

class DataSetValue(_message.Message):
    __slots__ = ("type", "int_value", "long_value", "float_value", "double_value", "boolean_value", "string_value")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LONG_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    type: int
    int_value: int
    long_value: int
    float_value: float
    double_value: float
    boolean_value: bool
    string_value: str
    def __init__(self, type: _Optional[int] = ..., int_value: _Optional[int] = ..., long_value: _Optional[int] = ..., float_value: _Optional[float] = ..., double_value: _Optional[float] = ..., boolean_value: bool = ..., string_value: _Optional[str] = ...) -> None: ...

class Template(_message.Message):
    __slots__ = ("version", "metrics", "parameters", "template_ref", "is_definition")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_REF_FIELD_NUMBER: _ClassVar[int]
    IS_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    version: str
    metrics: _containers.RepeatedCompositeFieldContainer[Metric]
    parameters: _containers.RepeatedCompositeFieldContainer[Parameter]
    template_ref: str
    is_definition: bool
    def __init__(self, version: _Optional[str] = ..., metrics: _Optional[_Iterable[_Union[Metric, _Mapping]]] = ..., parameters: _Optional[_Iterable[_Union[Parameter, _Mapping]]] = ..., template_ref: _Optional[str] = ..., is_definition: bool = ...) -> None: ...

class Parameter(_message.Message):
    __slots__ = ("name", "type", "int_value", "long_value", "float_value", "double_value", "boolean_value", "string_value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LONG_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: int
    int_value: int
    long_value: int
    float_value: float
    double_value: float
    boolean_value: bool
    string_value: str
    def __init__(self, name: _Optional[str] = ..., type: _Optional[int] = ..., int_value: _Optional[int] = ..., long_value: _Optional[int] = ..., float_value: _Optional[float] = ..., double_value: _Optional[float] = ..., boolean_value: bool = ..., string_value: _Optional[str] = ...) -> None: ...
