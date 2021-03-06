import threading

from .types import Singleton


class BaseSerializer(object):  # pragma: no cover
    def dumps(self, obj) -> bytes:
        """Serialize ``obj`` to a ``bytes``."""
        raise NotImplementedError

    def loads(self, s):
        """Deserialize ``s`` (a ``bytes``) to a Python object."""
        raise NotImplementedError


class SerializerRegistry(metaclass=Singleton):
    def __init__(self, serializers=None):
        self._serializers = serializers or {}
        self._lock = threading.Lock()

    def register(self, unique_name, serializer: BaseSerializer):
        """Register a new serializer.

        If the unique name already exists, it will not be overwritten.

        Arguments:
            unique_name (str): A convenience name for the serialization method.

            serializer (BaseSerializer): Object inherited from BaseSerializer.

        Raises:
            ValueError: If the unique_name already exists.
        """
        with self._lock:
            if unique_name in self._serializers:
                raise ValueError("serializer {} already exists".format(unique_name))
            self._serializers[unique_name] = serializer

    def unregister(self, unique_name):
        """Unregister registered serializer.

        Arguments:
            unique_name (str): Registered serializer name.

        Raises:
            KeyError: If a serializer by that name cannot be found.
        """
        with self._lock:
            try:
                self._serializers.pop(unique_name)
            except KeyError:
                raise KeyError("serializer {} not found".format(unique_name))

    def unregister_all(self):
        """Unregister all registered serializers"""
        with self._lock:
            self._serializers.clear()

    def get_by_name(self, unique_name):
        return self._serializers.get(unique_name, None)


class JSONSerializer(BaseSerializer):
    def __init__(self):
        import json

        self._json = json

    def dumps(self, obj):
        rv = self._json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        return bytes(rv, encoding="utf-8")

    def loads(self, s):
        return self._json.loads(s)


class MessagePackSerializer(BaseSerializer):
    def __init__(self):
        try:
            import msgpack

            self._msgpack = msgpack
        except ImportError:  # pragma: no cover
            raise ModuleNotFoundError("no msgpack module found.")

    def dumps(self, obj):
        return self._msgpack.dumps(obj, use_bin_type=True)

    def loads(self, s):
        return self._msgpack.loads(s, raw=False)


class PickleSerializer(BaseSerializer):
    def __init__(self):
        import pickle

        self._pickle = pickle

    def dumps(self, obj):
        return self._pickle.dumps(obj)

    def loads(self, s):
        return self._pickle.loads(s)


class ProtobufSerializer(BaseSerializer):
    def __init__(self, descriptor, dumper=None, loader=None):
        self._descriptor = descriptor
        self.dumper = dumper or self._default_dumper
        self.loader = loader or self._default_loader

    def _default_dumper(self, obj):
        return self._descriptor.SerializeToString(obj)

    def _default_loader(self, s):
        try:
            from google.protobuf import json_format
        except ImportError:  # pragma: no cover
            raise ModuleNotFoundError("no google.protobuf module found")
        return json_format.MessageToDict(
            self._descriptor.FromString(s),
            including_default_value_fields=True,
            preserving_proto_field_name=True,
            use_integers_for_enums=True,
        )

    def dumps(self, obj):
        if isinstance(obj, dict):
            obj = self._descriptor(**obj)
        if not isinstance(obj, self._descriptor):
            raise TypeError(
                "protocol buffer serializer `dumps` only support Dict/Pb object"
            )
        return self.dumper(obj)

    def loads(self, s):
        return self.loader(s)


registry = SerializerRegistry(
    serializers={
        "json": JSONSerializer(),
        "msgpack": MessagePackSerializer(),
        "pickle": PickleSerializer(),
    }
)
