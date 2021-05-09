"""Add syntatic sugar for configuration"""
import inspect
import warnings

default_clean = "[Tt]est*"

defaults = dict(
    rewrite_asserts=True,
    magics=True,
    clean=default_clean,
    addopts=("-q",),
    raise_on_error=False,
    run_in_thread=False,
    defopts=True,
)

current_config = dict(
    rewrite_asserts=False,
    magics=False,
    clean=default_clean,
    addopts=(),
    raise_on_error=False,
    run_in_thread=False,
    defopts=True,
)

_rewrite_context = None


class repr_meta(type):
    "Adapt repr for better display in completion"

    def __repr__(self):
        return f"<{self.__name__}>"


class keep(metaclass=repr_meta):
    """Sentinel for the config call"""

    pass


class default(metaclass=repr_meta):
    """Sentinel to mark a default argument"""

    pass


def gen_default_docs(func):
    defaults_docs = "\n".join(
        f"    * ``{key!s}``: ``{value!r}``" for key, value in defaults.items()
    )
    defaults_docs = defaults_docs.strip()

    func.__doc__ = func.__doc__.format(defaults_docs=defaults_docs)
    return func


@gen_default_docs
def autoconfig(
    rewrite_asserts=default,
    magics=default,
    clean=default,
    addopts=default,
    raise_on_error=default,
    run_in_thread=default,
    defopts=default,
):
    """Configure ``ipytest`` with reasonable defaults.

    Specifically, it sets:

    {defaults_docs}

    See :func:`ipytest.config` for details.
    """
    args = collect_args()
    config(
        **{
            key: replace_with_default(default, args[key], defaults.get(key))
            for key in current_config
        }
    )


def config(
    rewrite_asserts=keep,
    magics=keep,
    clean=keep,
    addopts=keep,
    raise_on_error=keep,
    run_in_thread=keep,
    defopts=keep,
):
    """Configure `ipytest`

    To update the configuration, call this function as in::

        ipytest.config(rewrite_asserts=True, raise_on_error=True)

    The following settings are supported:

    * ``rewrite_asserts`` (default: ``False``): enable ipython AST transforms
      globally to rewrite asserts
    * ``magics`` (default: ``False``): if set to ``True`` register the ipytest
      magics
    * ``clean`` (default: ``[Tt]est*``): the pattern used to clean variables
    * ``addopts`` (default: ``()``): pytest command line arguments to prepend
      to every pytest invocation. For example setting
      ``ipytest.config(addopts=['-qq'])`` will execute pytest with the least
      verbosity
    * ``raise_on_error`` (default: ``False``): if ``True``, unsuccessful
      invocations will raise a ``RuntimeError``
    * ``run_in_thread`` (default: ``False``): if ``True``, pytest will be run a
      separate thread. This way of running is required when testing async
      code with ``pytest_asyncio`` since it starts a separate event loop
    * ``defopts`` (default: ``True``): if ``True``, ipytest will add the
      current module to the arguments passed to pytest. If ``False`` only the
      arguments given and ``adopts`` are passed. Such a setup may be helpful
      to customize the test selection
    """
    args = collect_args()
    new_config = {
        key: replace_with_default(keep, args[key], current_config.get(key))
        for key in current_config
    }

    if new_config["rewrite_asserts"] != current_config["rewrite_asserts"]:
        configure_rewrite_asserts(new_config["rewrite_asserts"])

    if new_config["magics"] != current_config["magics"]:
        configure_magics(new_config["magics"])

    current_config.update(new_config)
    return dict(current_config)


def configure_rewrite_asserts(enable):
    global _rewrite_context

    from IPython import get_ipython
    from ._pytest_support import RewriteContext

    if enable:
        assert _rewrite_context is None
        _rewrite_context = RewriteContext(shell=get_ipython())
        _rewrite_context.__enter__()

    else:
        assert _rewrite_context is not None
        _rewrite_context.__exit__(None, None, None)
        _rewrite_context = None


def configure_magics(enable):
    from IPython import get_ipython
    from ._pytest_support import IPyTestMagics

    if enable:
        get_ipython().register_magics(IPyTestMagics)

    else:
        warnings.warn("IPython does not support de-registering magics.")


def replace_with_default(sentinel, value, default):
    return default if value is sentinel else value


def collect_args():
    frame = inspect.currentframe()
    frame = frame.f_back
    args, _, _, values = inspect.getargvalues(frame)
    return {key: values[key] for key in args}
