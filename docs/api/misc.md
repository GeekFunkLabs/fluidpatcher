# Miscellaneous: Config and Exceptions

This section covers two minor parts of the API that can be useful
when writing programs with FluidPatcher:

* Managing the **global configuration file**
* **Exceptions** raised when a bank file fails to load

## Global Configuration

FluidPatcher configuration is stored at
`~/.config/fluidpatcher/fluidpatcherconf.yaml`,
or the location referenced by the environment variable
`FLUIDPATCHER_CONFIG` if set.

### Loading Config

Loading happens *once* at import, and the data is stored in the global
variable CONFIG. When loading, any key ending in `_path` is
automatically converted into a `Path` object internally,
so paths behave consistently across platforms.

::: fluidpatcher.config.save_config

This function can be used to store modified fluidsettings or add custom
states that persist across FluidPatcher imports.

For example, a program might store the current bank, so that it can be
loaded automatically next time the program starts:

```python
CONFIG["currentbank_path"] = Path(bankfile)
```

By choosing a key that ends in `_path` it gets properly serialized by
`save_config()` and parsed on import, like the other path settings.

## Bank File Errors

All bank-related errors derive from a single base class `BankError`.
This makes it easy to catch *any* bank failure at a high level, while
still getting detailed diagnostics.

::: fluidpatcher.bankfiles.BankSyntaxError
    options:
      members: false

This error means the YAML itself is improperly formatted.

Typical issues include:

* Bad indentation
* Missing colons
* Unterminated flow mappings
* Invalid YAML literals

When possible, the error includes line and column information pointing
directly at the problem.

Example output:

```shell
mapping values are not allowed here at line 27, column 14
```

This error happens *before* fluidpatcher looks at musical meaning—
nothing in the file is interpreted yet.

::: fluidpatcher.bankfiles.BankValidationError

This error means the YAML is valid, but the contents don’t make sense
to fluidpatcher.

Common causes include:

* Missing required keys
* Unknown rule or message types
* Invalid parameter ranges
* Null values (not allowed)

Validation errors include a **path** that points to the failing node
in the bank structure.

Example output:

```shell
MidiRule type 'ntoe' not recognized in patches.Rhodes.rules.2
```

This tells you exactly where fluidpatcher gave up, without requiring
guesswork.

## Summary

* Global config can be modified and store state variables
* Bank files are validated strictly, with clear diagnostics
* Syntax errors mean “bad YAML”
* Validation errors mean “valid YAML, wrong meaning”

