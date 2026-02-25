from collections import namedtuple

URLComponents = namedtuple(
    typename="URLComponents",
    field_names=["scheme", "netloc", "path", "params", "query", "fragment"],
)
