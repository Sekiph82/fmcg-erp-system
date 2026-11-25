"""M45.S01.T018 configuration bundles (DB part needs M45_DB=1 and M45_DB2_URL: a second disposable database).

Round trip between two databases: configuration created in "staging" (pipeline + stage, custom field + option, object
type, sequence + step, workflow with a published graph) is exported, the dry run on "production" lists creates and
writes nothing, apply creates everything with new ids and resolved references, a second plan is all unchanged; a
changed bundle updates; a tampered bundle and another schema revision are refused; no customer data is inside.
"""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services import config_bundle_service as cbs

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1" or not os.environ.get("M45_DB2_URL"),
                        reason="requires two task-owned disposable PostgreSQL databases")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _seed(db, s):
    from app.models.crm import CRMPipeline, CRMPipelineStage, CRMSequence, CRMSequenceStep, CRMStageType, CRMWorkflow, CRMWorkflowVersion
    from app.models.custom_fields import CustomFieldDefinition, CustomFieldOption, EntityType, FieldType
    from app.models.custom_objects import CustomObjectType
    from app.models.sales import Customer
    p = CRMPipeline(name=f"Key accounts {s}", is_default=False)
    db.add(p)
    await db.flush()
    db.add(CRMPipelineStage(stage_code=f"KA-{s}", stage_name="Tasting", stage_type=CRMStageType.OPPORTUNITY, sequence_no=1,
                            default_probability=30, pipeline_id=p.id))
    f = CustomFieldDefinition(entity_type=EntityType.CUSTOMER, field_code=f"fridge_{s}", field_label="Fridge", field_type=FieldType.SELECT)
    db.add(f)
    await db.flush()
    db.add(CustomFieldOption(custom_field_id=f.custom_field_id, option_value="YES", option_label="Yes"))
    db.add(CustomObjectType(key=f"cooler{s}", label="Cooler", label_plural="Coolers", display_field="serial",
                            fields=[{"key": "serial", "label": "Serial", "type": "text", "required": True, "unique": True}]))
    seq = CRMSequence(name=f"Welcome {s}")
    db.add(seq)
    await db.flush()
    db.add(CRMSequenceStep(sequence_id=seq.id, step_no=1, delay_days=0, subject="Karibu POVU", body="Hello {first_name}"))
    wf = CRMWorkflow(name=f"Won follow-up {s}", trigger_event="won")
    db.add(wf)
    await db.flush()
    v = CRMWorkflowVersion(workflow_id=wf.id, version_no=1, status="PUBLISHED", created_at=datetime.now(timezone.utc),
                           graph={"nodes": [{"id": "t", "type": "trigger", "config": {"event": "won"}}], "edges": []})
    db.add(v)
    await db.flush()
    wf.published_version_id = v.id
    db.add(Customer(code=f"SECRET-{s}", name=f"Secret Customer {s}", currency="KES", email=f"secret{s}@povu-demo.test"))
    await db.commit()


@DB
@pytest.mark.asyncio
async def test_round_trip_between_two_databases():
    from app.db.session import AsyncSessionLocal
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as staging:
        await _seed(staging, s)
        bundle = await cbs.export(staging)
    raw = json.dumps(bundle)
    assert f"Secret Customer {s}" not in raw and f"secret{s}@" not in raw and "customers" not in bundle["items"]
    eng = create_async_engine(os.environ["M45_DB2_URL"])
    Prod = async_sessionmaker(eng, expire_on_commit=False)
    try:
        async with Prod() as prod:
            steps = await cbs.plan(prod, bundle)
            mine = [x for x in steps if s in x["key"]]
            assert mine and all(x["action"] == "create" for x in mine)
            await prod.rollback()
            from sqlalchemy import select
            from app.models.crm import CRMPipeline
            assert (await prod.execute(select(CRMPipeline).where(CRMPipeline.name == f"Key accounts {s}"))).first() is None   # dry run wrote nothing
            out = await cbs.apply(prod, bundle, "tester")
            await prod.commit()
            assert out["created"] >= 7
        async with Prod() as prod:
            from app.models.crm import CRMPipelineStage, CRMWorkflow, CRMWorkflowVersion
            from app.models.custom_fields import CustomFieldDefinition, CustomFieldOption
            stage = (await prod.execute(select(CRMPipelineStage).where(CRMPipelineStage.stage_code == f"KA-{s}"))).scalar_one()
            pipe = (await prod.execute(select(CRMPipeline).where(CRMPipeline.name == f"Key accounts {s}"))).scalar_one()
            assert stage.pipeline_id == pipe.id                                                  # reference re-resolved
            fdef = (await prod.execute(select(CustomFieldDefinition).where(CustomFieldDefinition.field_code == f"fridge_{s}"))).scalar_one()
            assert (await prod.execute(select(CustomFieldOption).where(CustomFieldOption.custom_field_id == fdef.custom_field_id))).scalar_one().option_value == "YES"
            wf = (await prod.execute(select(CRMWorkflow).where(CRMWorkflow.name == f"Won follow-up {s}"))).scalar_one()
            ver = (await prod.execute(select(CRMWorkflowVersion).where(CRMWorkflowVersion.workflow_id == wf.id))).scalar_one()
            assert ver.status == "DRAFT" and wf.published_version_id is None                    # must be published again
            again = await cbs.plan(prod, bundle)
            assert all(x["action"] == "unchanged" for x in again if s in x["key"] and x["table"] != "crm_workflows")
            changed = json.loads(json.dumps(bundle))
            for st in changed["items"]["crm_pipeline_stages"]:
                if st["stage_code"] == f"KA-{s}":
                    st["stage_name"] = "Tasting & sampling"
            with pytest.raises(cbs.BundleError):                                                 # tampered (checksum)
                await cbs.plan(prod, changed)
            changed["sha256"] = hashlib.sha256(json.dumps(changed["items"], sort_keys=True, default=str).encode()).hexdigest()
            upd = [x for x in await cbs.plan(prod, changed) if x["key"] == f"KA-{s}"]
            assert upd[0]["action"] == "update" and upd[0]["changed"] == ["stage_name"]
            skip = [x for x in await cbs.plan(prod, changed, "skip_existing") if x["key"] == f"KA-{s}"]
            assert skip[0]["action"] == "skip"
            await cbs.apply(prod, changed, "tester")
            await prod.commit()
            await prod.refresh(stage)
            assert stage.stage_name == "Tasting & sampling"
            other = {**changed, "schema_revision": "19990101_0001"}
            with pytest.raises(cbs.BundleError) as e:
                await cbs.plan(prod, other)
            assert e.value.status == 409
    finally:
        await eng.dispose()
