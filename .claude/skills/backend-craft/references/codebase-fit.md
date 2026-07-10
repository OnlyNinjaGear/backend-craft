# Codebase fit

Read this before refactoring or adding structure to an existing backend.

The goal is to preserve local architecture unless it is the source of the
problem. Do not impose a generic clean architecture diagram over a codebase that
already has working conventions.

## Inventory first

Before changing structure, identify:

- framework and entrypoints
- package/module boundaries
- dependency direction
- naming conventions
- existing service/repository/use-case patterns
- test layout
- error handling style
- configuration and dependency injection style

Hard rule: verify commands MUST use the package manager detected from the
lockfile (`pnpm-lock.yaml` -> pnpm, `yarn.lock` -> yarn, `package-lock.json` ->
npm; `uv.lock` -> uv, `poetry.lock` -> poetry). Writing `npm` commands into a
pnpm repo is a defect: `npm install` creates a conflicting lockfile.

## Refactor rule

Change the smallest boundary that owns the behavior.

Prefer:

1. delete unnecessary abstraction
2. use existing helper/pattern
3. fix owning module
4. split only when two responsibilities are proven
5. introduce new abstraction only when duplication or risk is concrete

## Dumping-ground rule

Files named `utils`, `helpers`, `misc`, `common`, or `manager` are not banned by
name alone. They are banned when they accumulate unrelated responsibilities.

Safe pattern:

- name module by domain capability, not implementation vagueness
- move functions near the owner that changes with them
- keep public surface small

## Dependency direction

Handlers/controllers may depend on use cases/services. Use cases may depend on
interfaces/ports. Infrastructure implements those ports. Repositories do not
call handlers/controllers.

But local convention wins if it is coherent. Do not rewrite layers just to match
this sentence.

## Naming

Names should encode domain intent:

- functions: verb phrase with business action
- modules/classes: owned concept
- booleans: predicate shape (`is_`, `has_`, `can_`, `should_`)
- avoid `data`, `info`, `obj`, `manager`, `processor`, `handler` unless the
  surrounding framework/domain makes the role precise

## Verifier

For refactors, prove behavior preservation:

- existing tests pass
- new tests cover moved behavior when existing coverage is missing
- public contract diff is empty or intentionally documented
- no unrelated formatting churn
