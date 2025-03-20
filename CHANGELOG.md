# CHANGELOG


## v0.8.5 (2025-03-19)

### Bug Fixes

- **ci**: Proper cross-platform Docker images
  ([`dfa0d6b`](https://github.com/r-near/nearc/commit/dfa0d6b71877f823d674dbf2f4b0d71744247df3))


## v0.8.4 (2025-03-19)

### Bug Fixes

- **reproducible**: Update Docker mount path to /home/near/code
  ([#36](https://github.com/r-near/nearc/pull/36),
  [`bdde77f`](https://github.com/r-near/nearc/commit/bdde77f97be6666d44f71be3481b0ceaafb69f4c))


## v0.8.3 (2025-03-19)

### Bug Fixes

- **ci**: Support multi-platform builds ([#34](https://github.com/r-near/nearc/pull/34),
  [`efdb691`](https://github.com/r-near/nearc/commit/efdb6916633dd15b4444734204d02b98155f0723))


## v0.8.2 (2025-03-19)

### Bug Fixes

- **reproducible**: Automatically set up dependencies in container builds
  ([#35](https://github.com/r-near/nearc/pull/35),
  [`2fff8f8`](https://github.com/r-near/nearc/commit/2fff8f84be8eaa19430bebb74ef501ee8a268106))

* save

* cleanup

* lockfile

* linting

* Lockfile issues

### Chores

- **deps**: Bump near-abi-py from 0.3.0 to 0.4.0 ([#29](https://github.com/r-near/nearc/pull/29),
  [`b09efe4`](https://github.com/r-near/nearc/commit/b09efe4b69235c175a31ade04c860bb113ea00c2))

Bumps near-abi-py from 0.3.0 to 0.4.0.

--- updated-dependencies: - dependency-name: near-abi-py dependency-type: direct:production

update-type: version-update:semver-minor ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump rich-click from 1.8.6 to 1.8.8 ([#27](https://github.com/r-near/nearc/pull/27),
  [`fb276d0`](https://github.com/r-near/nearc/commit/fb276d082b400df8246e20d42776acc119884e7c))

Bumps [rich-click](https://github.com/ewels/rich-click) from 1.8.6 to 1.8.8. - [Release
  notes](https://github.com/ewels/rich-click/releases) -
  [Changelog](https://github.com/ewels/rich-click/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/ewels/rich-click/compare/v1.8.6...v1.8.8)

--- updated-dependencies: - dependency-name: rich-click dependency-type: direct:production

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump types-zstd from 1.5.6.5.20250304 to 1.5.6.6.20250306
  ([#26](https://github.com/r-near/nearc/pull/26),
  [`d9ac0ab`](https://github.com/r-near/nearc/commit/d9ac0ab74c28c46f5621c627dc4cbee0a0636369))

Bumps [types-zstd](https://github.com/python/typeshed) from 1.5.6.5.20250304 to 1.5.6.6.20250306. -
  [Commits](https://github.com/python/typeshed/commits)

--- updated-dependencies: - dependency-name: types-zstd dependency-type: direct:production

update-type: version-update:semver-patch ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Create dependabot.yml
  ([`66b7f70`](https://github.com/r-near/nearc/commit/66b7f7076f67c03831431f9bad8f6d57f25a8b13))


## v0.8.1 (2025-03-14)

### Bug Fixes

- **builder**: Cleanup files
  ([`35a3a26`](https://github.com/r-near/nearc/commit/35a3a269308f02ed5c364af26a18fb411d3c48a8))


## v0.8.0 (2025-03-14)

### Features

- Auto inject exports ([#25](https://github.com/r-near/nearc/pull/25),
  [`a84de7e`](https://github.com/r-near/nearc/commit/a84de7eb62731e83c0afce68658daf09ee081605))


## v0.7.3 (2025-03-14)

### Bug Fixes

- Check for C keywords in export function names ([#24](https://github.com/r-near/nearc/pull/24),
  [`3b10901`](https://github.com/r-near/nearc/commit/3b109019d5a6463438f4a5adc4d3e99a0df7ee59))


## v0.7.2 (2025-03-13)

### Bug Fixes

- **micropython**: Update to latest ([#22](https://github.com/r-near/nearc/pull/22),
  [`613241d`](https://github.com/r-near/nearc/commit/613241de03021bae6d20adfea2ad999bd2169e02))


## v0.7.1 (2025-03-12)

### Bug Fixes

- **analyzer**: Add `multi_callback` decorator
  ([`cc6a86c`](https://github.com/r-near/nearc/commit/cc6a86c37627b6c4caa3af067d8c8faf318e108d))


## v0.7.0 (2025-03-11)

### Features

- Add --single-file flag to skip local module discovery
  ([#20](https://github.com/r-near/nearc/pull/20),
  [`1e4e06b`](https://github.com/r-near/nearc/commit/1e4e06b0100f55862f474db0273e253ff483e018))

Add a new CLI option to compile only the specified file without including other modules from the
  same directory. This is useful for unit testing and isolated contract development.


## v0.6.1 (2025-03-09)

### Bug Fixes

- Update MicroPython ([#19](https://github.com/r-near/nearc/pull/19),
  [`4219551`](https://github.com/r-near/nearc/commit/42195510edc9c1c5df0b82d0774b57b4ace20152))


## v0.6.0 (2025-03-07)

### Features

- **deps**: Bump near-abi-py ([#17](https://github.com/r-near/nearc/pull/17),
  [`3beb9b8`](https://github.com/r-near/nearc/commit/3beb9b8b2505ea6cb473b752bde905d4ca7b85ae))


## v0.5.5 (2025-03-07)

### Bug Fixes

- **ci**: Don't persist credentials so CI can use PAT
  ([`9eb143a`](https://github.com/r-near/nearc/commit/9eb143ac664c6a89d5e262f51c5af4d0b250c978))


## v0.5.4 (2025-03-07)

### Bug Fixes

- **ci**: Use correct access token to trigger builds
  ([`a4accc8`](https://github.com/r-near/nearc/commit/a4accc852f12de4478cf9497b744bfd85ef08736))


## v0.5.3 (2025-03-07)

### Bug Fixes

- **ci**: Allow triggering on workflow dispatch
  ([`bca730a`](https://github.com/r-near/nearc/commit/bca730af23be6ffd24cb35db872490a2e9b15e5f))


## v0.5.2 (2025-03-06)

### Bug Fixes

- **ci**: Don't publish, but build Docker image
  ([`0dc7c2c`](https://github.com/r-near/nearc/commit/0dc7c2cec4b1f719b98ba51cd4fe8d18a463007a))


## v0.5.1 (2025-03-06)

### Bug Fixes

- **ci**: Update version automatically
  ([`2a6eb45`](https://github.com/r-near/nearc/commit/2a6eb45e45475d9b3e8bec1f1368319abe7ff42d))

### Chores

- **release**: 0.5.1 [skip ci]
  ([`480fa0f`](https://github.com/r-near/nearc/commit/480fa0fe1b453730793caae61eb4b3f0a184b775))


## v0.5.0 (2025-03-06)

### Chores

- **release**: 0.5.0 [skip ci]
  ([`f35e90c`](https://github.com/r-near/nearc/commit/f35e90c265900d84282812fc54b24fbbcdf07a2e))

### Features

- **ci**: Add auto-release ([#16](https://github.com/r-near/nearc/pull/16),
  [`7a73387`](https://github.com/r-near/nearc/commit/7a73387883bbd45e7a0cd281c8eaa18d91ff7307))

* feat(release): Add auto-release

* Run on main

* Simplify package


## v0.4.0 (2025-03-06)

### Chores

- **release**: 0.4.0 [skip ci]
  ([`8d4b77e`](https://github.com/r-near/nearc/commit/8d4b77e6799bbcb21c53f7fb621091ad3f6dc947))

### Features

- Auto-detect Contract Files and Improve Module Discovery
  ([#14](https://github.com/r-near/nearc/pull/14),
  [`8474fd3`](https://github.com/r-near/nearc/commit/8474fd32fd5886024992d7e64f0399e4801fc7ca))

* feat: Add support for importing multi-file projects

* Update README

* feat: Multi-file builds

* Linting

- Update MicroPython ([#15](https://github.com/r-near/nearc/pull/15),
  [`704a21b`](https://github.com/r-near/nearc/commit/704a21b14967f97c77e29b2e6326f3e769c67088))


## v0.3.7 (2025-03-06)

### Bug Fixes

- **metadata**: Match source code spec
  ([`883e3b6`](https://github.com/r-near/nearc/commit/883e3b65c39d3fd6f9c23e77f5be244dafbfc1b9))

### Chores

- Update docs
  ([`fc51ee9`](https://github.com/r-near/nearc/commit/fc51ee9ff178923c5dcf13c7c9fdcba4321a1fe4))

### Features

- Add commit hash to contract metadata ([#12](https://github.com/r-near/nearc/pull/12),
  [`9890e2b`](https://github.com/r-near/nearc/commit/9890e2b8e07eadae617a2c00a0fdc09a3f0cd45b))


## v0.3.6 (2025-03-05)

### Bug Fixes

- **deterministic**: Sort all exports for deterministic builds
  ([#11](https://github.com/r-near/nearc/pull/11),
  [`9fbad8d`](https://github.com/r-near/nearc/commit/9fbad8d6dd55c6af066368faa904762acc45550a))

* fix: more issues with sorting exports

* chore: Bump version


## v0.3.5 (2025-03-05)

### Bug Fixes

- Bump version
  ([`bd531f6`](https://github.com/r-near/nearc/commit/bd531f61b4f4c347d67b56ab5a79a898280dcf35))

- Deterministic order for manifest files ([#10](https://github.com/r-near/nearc/pull/10),
  [`8da2049`](https://github.com/r-near/nearc/commit/8da20493c4104d70966a337e06447b5987e67f04))

* fix: Deterministic order for manifest files

* Don't build docker images for PRs

### Chores

- Add linting ([#6](https://github.com/r-near/nearc/pull/6),
  [`ee662c3`](https://github.com/r-near/nearc/commit/ee662c3d382ee79f6a5a9e63d2e4642e1a243655))

- Bump version
  ([`92d0897`](https://github.com/r-near/nearc/commit/92d0897a364861c2bdccfcc975b97a699a0d40d0))

### Features

- Add ABI support ([#3](https://github.com/r-near/nearc/pull/3),
  [`7602d36`](https://github.com/r-near/nearc/commit/7602d36af73a280d9b62f1d99d65624409bce6c6))

- Add Automatic NEP-330 Metadata Support ([#1](https://github.com/r-near/nearc/pull/1),
  [`3741b3e`](https://github.com/r-near/nearc/commit/3741b3e48bd6ccf54d625a6178563014323a79f1))

* feat: Add Automatic NEP-330 Metadata Support

* fix doc

- Add prettier output for compiler
  ([`cdff4d2`](https://github.com/r-near/nearc/commit/cdff4d2a9badb685100455b4a1795e6edb741912))

- Publish Docker images ([#8](https://github.com/r-near/nearc/pull/8),
  [`0018794`](https://github.com/r-near/nearc/commit/00187949a2ce6afc8834a43219e113c41c622ae0))

- Reproducible Builds with Docker ([#9](https://github.com/r-near/nearc/pull/9),
  [`0bcbc73`](https://github.com/r-near/nearc/commit/0bcbc73d8059898cc0bd5da2daeea2500bfeee21))

* feat: Support reproducible builds with Docker

* Update build command

* Better docs

- **metadata**: Improved contract metadata handling ([#7](https://github.com/r-near/nearc/pull/7),
  [`87d201c`](https://github.com/r-near/nearc/commit/87d201c76ad3fb985fb0715f57f3f4c5fdf1bd59))

* feat(metadata): Improved contract metadata handling

* chore: Bump version

### Refactoring

- Clean up compiler code
  ([`8b05a78`](https://github.com/r-near/nearc/commit/8b05a786f24bee18b33e61f42f00154ea9649eb2))

- Modular Architecture ([#2](https://github.com/r-near/nearc/pull/2),
  [`79bb892`](https://github.com/r-near/nearc/commit/79bb8926454f766632da6fdca30278603cade5fb))

* refactor: Break up into modules

* Update version


## v0.1.2 (2025-03-03)

### Build System

- Non-zero exit code on errors
  ([`817d2da`](https://github.com/r-near/nearc/commit/817d2dac8d78239ed1b57a6b7a97074fce10a934))

### Documentation

- Added Examples section with the references to already deployed contracts
  ([`9c8ece6`](https://github.com/r-near/nearc/commit/9c8ece6ee9964a44fccb15035ab9dbef712e2e41))
