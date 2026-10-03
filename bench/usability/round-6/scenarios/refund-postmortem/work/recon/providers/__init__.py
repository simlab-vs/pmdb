"""Provider adapters: each turns a provider's raw event into a Txn."""

from . import kestrel, lumen, novapay

ADAPTERS = {
    "kestrel": kestrel.normalize,
    "lumen": lumen.normalize,
    "novapay": novapay.normalize,
}


class UnknownProvider(KeyError):
    pass


def adapter_for(provider):
    try:
        return ADAPTERS[provider]
    except KeyError:
        raise UnknownProvider(provider) from None
