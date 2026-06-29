# backend/tests/test_multitenant_autonomous.py
"""P3: autonomous verification + anchoring must process EVERY tenant, not just default."""
import os

import boto3
from moto import mock_aws

from forward_ledger import Kind, Ledger, Prediction, list_tenants
from forward_ledger.dynamo_store import DynamoDBStore

TABLE = "nexus-mt"


def _make():
    boto3.resource("dynamodb", region_name="us-east-1").create_table(
        TableName=TABLE,
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"},
                   {"AttributeName": "sk", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                              {"AttributeName": "sk", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST")


def _seal(tenant, d):
    s = DynamoDBStore(table_name=TABLE, tenant=tenant)
    s.register_tenant()
    Ledger(s).append(Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4],
                                survivor=0, confidence=0.6, why="w", watch="t",
                                kind=Kind.FORWARD, oracle_ref="seed:" + d))


@mock_aws
def test_registry_enumerates_every_tenant():
    _make()
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["NEXUS_DDB_TABLE"] = TABLE
    try:
        _seal("acme", "a"); _seal("globex", "b"); _seal("initech", "c")
        assert sorted(list_tenants()) == ["acme", "globex", "initech"]
    finally:
        os.environ.pop("NEXUS_DDB_TABLE", None)


@mock_aws
def test_autonomous_loop_processes_all_tenants():
    _make()
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["NEXUS_DDB_TABLE"] = TABLE
    try:
        _seal("acme", "a"); _seal("globex", "b")
        import anchor_handler
        import resolver_handler
        r = resolver_handler.handler({}, None)
        assert r["tenants"] == 2 and {x["tenant"] for x in r["results"]} == {"acme", "globex"}
        a = anchor_handler.handler({}, None)
        assert a["tenants"] == 2
        assert all("merkle_root" in x for x in a["results"])   # each tenant anchored
    finally:
        os.environ.pop("NEXUS_DDB_TABLE", None)
