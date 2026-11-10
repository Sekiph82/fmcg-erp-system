# M26.S01.T001 — Machine/operator qualification model

## Implementation

- Added `MachineSkillRequirement`, scoped to exactly one machine or work center and linked to the existing `training_skills` registry.
- Requirements store a supported minimum skill level, certification-required flag, active state, and notes. Partial unique indexes prevent duplicate skills per resource without blocking the other resource type.
- Linked existing `OperatorSkillCert` rows to the canonical skill registry through a nullable foreign key, preserving legacy certifications.
- Added ORM relationships and an additive Alembic revision after the current local head. The migration accounts for the squashed baseline's metadata-driven `create_all`, so it can upgrade both baseline-created and already-existing schemas.
- No employee/factory records were fabricated. No API or assignment behavior was added; expiry, enforcement, and audited override remain in their M26 task scopes.

## Lightweight evidence

- `python -m compileall -q app/models/machine_operator.py app/models/production_advanced.py app/models/__init__.py alembic/versions/20261108_0018_m26_machine_skill_requirements.py` — passed.
- SQLAlchemy model import and `configure_mappers()` smoke check — passed; qualification columns, constraints, foreign keys, and relationships registered.
- PostgreSQL `CreateTable` DDL compilation smoke check — passed.
- `alembic heads` — `20261108_0018` is the single head.
- `git diff --check` — passed.

## Pending milestone acceptance

Disposable-PostgreSQL upgrade/constraint behavior, the M26 consolidated regression suite, and consolidated independent code/security review are deferred to M26 acceptance per the milestone testing policy. This task is implemented but not yet accepted.
