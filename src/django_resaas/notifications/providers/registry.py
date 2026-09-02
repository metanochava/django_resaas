class NotificationProviderRegistry:
    """`register(channel, name, provider)` - providers are looked up by
    channel + name (or just channel, for the channel's default), never
    imported directly by the engine/worker. This is also what lets tests
    swap in Fake* providers without touching any calling code."""

    _providers = {}  # {channel: {name: provider_instance}}
    _defaults = {}  # {channel: name}

    @classmethod
    def register(cls, channel, name, provider, *, default=False):
        cls._providers.setdefault(channel, {})[name] = provider

        if default or channel not in cls._defaults:
            cls._defaults[channel] = name

    @classmethod
    def get(cls, channel, name=None):
        name = name or cls._defaults.get(channel)
        if not name:
            return None
        return cls._providers.get(channel, {}).get(name)

    @classmethod
    def unregister_all(cls):
        """Test helper."""
        cls._providers = {}
        cls._defaults = {}
