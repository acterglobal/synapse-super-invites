# Super Inivitation flow for Synapse Matrix Homeserver

Provides extended support for users to invite other users to rooms via an invitation token

## Installation

From the virtual environment that you use for Synapse, install this module with:

```shell
pip install path/to/synapse-super-invites
```

(If you run into issues, you may need to upgrade `pip` first, e.g. by running
`pip install --upgrade pip`)

Then alter your homeserver configuration, adding to your `modules` configuration:

```yaml
modules:
  - module: synapse_super_invites.SynapseSuperInvites
    config:
      generate_registration_tokens: true # default: false - whether or not the invite tokens are also usable as registration tokens
      enable_web: true # default: false - not yet ready web/html management app
```

## Usage

## Changelog

**0.8.0b2** - 2023-11-17:

- Fix broken import of `resource.*`

**0.8.0b1** - 2023-11-17:

- First attempt at releasing

## Development

In a virtual environment with pip ≥ 21.1, run

```shell
pip install -e .[dev]
```

To run the unit tests, you can either use:

```shell
tox -e py
```

or

```shell
trial tests
```

To run the linters and `mypy` type checker, use `./scripts-dev/lint.sh`.
