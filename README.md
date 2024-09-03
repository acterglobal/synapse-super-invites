# Super Invitation flow for Synapse Matrix Homeserver

![GitHub CI status main](https://img.shields.io/github/checks-status/acterglobal/synapse-super-invites/main) ![PyPI - Version](https://img.shields.io/pypi/v/synapse_super_invites)

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
      sql_url: "sqlite:///data/super_invites.db"
      generate_registration_token: true # default: false - whether or not the invite tokens are also usable as registration tokens
      enable_web: true # default: false - not yet ready web/html management app
```

### Using [the ansible script]

If you are using the awesome [matrix-docker-ansible-deploy suite by spantaleev]() (thanks, mate! Great work!),
you can install and configure module by setting the following to your `vars.yml` for the corresponding server:

```yaml
# make sure we build a custom docker image for synapse
matrix_synapse_container_image_customizations_enabled: true
# install the super invites with pip
matrix_synapse_container_image_customizations_dockerfile_body_custom: |
  RUN pip install synapse_super_invites

# add super-invites to the modules and configure it
matrix_synapse_modules:
  - module: "synapse_super_invites.SynapseSuperInvites"
    config:
      sql_url: "sqlite://///matrix-media-store-parent/super_invites.db"
      generate_registration_token: true
```

This creates a super_invites database persistent across restarts and docker rebuilds, you can find in `/matrix/synapse/storage` on your host.

### Confirming

You can confirm the installation went well by trying to access the path `/_synapse/client/super_invites/tokens` on your matrix server. If the module is available this will return with a `401` with `errCode: M_MISSING_TOKEN`. If it isn't available you will get a `404` with `"errcode: "M_UNRECOGNIZED"`.

## Usage

## Changelog

**0.8.4** - 2024-09-03:

- [Fix] DMs are encrypted of course, with tests.

**0.8.3** - 2024-05-28:

- [Fix] Skip room if adding fails, but continue with adding to the others, track errors in db

**0.8.2** - 2024-05-11:

- Support for receiving info about a token without redeeming it, #2
- Fix to mark DMs as direct (includes tests), #7
- Fix for pyproject URLs, #1, thanks to @HarHarLinks
- Allow API caller to not disable registration token creation
- Clean up types

**0.8.1** - 2023-11-24:

- ensure deleted tokens stay unaccessible -- also to the owner

**0.8.0** - 2023-11-24:

- documentation about how to use this with the docker-ansible-scripts
- roadmap info added

**0.8.0b3** - 2023-11-17:

- Migration file inclusion

**0.8.0b2** - 2023-11-17:

- Fix broken import of `resource.*`

**0.8.0b1** - 2023-11-17:

- First attempt at releasing

## Roadmap

What is missing for a 1.0?

- Allow room-admins to know about all SuperInviteTokens for the given room
- Web-Frontend to allow anyone to use this (is this even possible?)

## Development

In a virtual environment with pip ≥ 21.1, run

```shell
pip install -e .[dev]
```

To run the unit tests, you can either use:

```shell
tox -e py
```

To run the linters and `mypy` type checker, use `./scripts-dev/lint.sh`.

### Generating new db version

Make your changes in `model/`, then run:

```
alembic revision --autogenerate -m "Description message"
```
