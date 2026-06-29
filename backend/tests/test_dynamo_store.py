# backend/tests/test_dynamo_store.py
"""DynamoDBStore satisfies the LedgerStore contract and isolates tenants.
Runs fully offline against moto's in-memory DynamoDB — no AWS, no network."""
import os

import boto3
import pytest
from moto import mock_aws

from forward_ledger import Kind, Ledger, Prediction
from forward_ledger.dynamo_store import DynamoDBStore

TABLE = "nexus-decision-store-test"


def _make_table():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=TABLE,
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"},
                   {"AttributeName": "sk", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                              {"AttributeName": "sk", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


def _pred(d, p=0.6, asm=None):
    return Prediction(decision=d, branches=["s", "x"], weights=[p, round(1 - p, 4)],
                      survivor=0, confidence=p, why="w", watch="t",
                      kind=Kind.FORWARD, oracle_ref="seed:" + d, assumptions=asm or [])


@mock_aws
def test_store_roundtrip_and_chain():
    _make_table()
    os.environ["AWS_REGION"] = "us-east-1"
    L = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    e1 = L.append(_pred("alpha", 0.8, asm=["demand holds"]), created_at=1.0)
    L.append(_pred("beta", 0.3), created_at=1.0)
    assert L.verify() is True
    # reload from a fresh store instance -> durability + ordering + chain integrity
    L2 = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    assert [e.prediction["decision"] for e in L2.all()] == ["alpha", "beta"]
    assert L2.verify() is True
    # resolution emits cf + asm sibling rows, and update() persists outcome
    L2.resolve(e1.id, survived=False, ref="oracle:x", at=10.0)
    assert L2.assumption_rows()  # asm log populated
    assert L2.counterfactual_rows()  # cf log populated
    L3 = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    assert L3.by_id(e1.id).survived is False


@mock_aws
def test_tenant_isolation():
    _make_table()
    os.environ["AWS_REGION"] = "us-east-1"
    a = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    g = Ledger(DynamoDBStore(table_name=TABLE, tenant="globex"))
    a.append(_pred("acme-secret"), created_at=1.0)
    g.append(_pred("globex-secret"), created_at=1.0)
    # neither tenant can see the other's decisions, though they share one table
    assert [e.prediction["decision"] for e in Ledger(
        DynamoDBStore(table_name=TABLE, tenant="acme")).all()] == ["acme-secret"]
    assert [e.prediction["decision"] for e in Ledger(
        DynamoDBStore(table_name=TABLE, tenant="globex")).all()] == ["globex-secret"]


def test_invalid_tenant_rejected():
    with pytest.raises(ValueError):
        DynamoDBStore(table_name=TABLE, tenant="../etc/passwd")


@mock_aws
def test_concurrent_writers_never_lose_a_sealed_decision():
    """Regression for the critical C1 concurrency bug: two ledgers on the same partition
    both computing seq 0 must NOT silently overwrite — the loser re-syncs and retries."""
    _make_table()
    os.environ["AWS_REGION"] = "us-east-1"
    a = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    b = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    a.append(_pred("acquire competitor"))
    b.append(_pred("enter new market"))      # raced a at seq 0 -> must retry to seq 1
    final = Ledger(DynamoDBStore(table_name=TABLE, tenant="acme"))
    decisions = {e.prediction["decision"] for e in final.all()}
    assert decisions == {"acquire competitor", "enter new market"}   # nothing dropped
    assert [e.seq for e in final.all()] == [0, 1]                    # contiguous, append-only
    assert final.verify() is True


@mock_aws
def test_many_racing_writers_produce_contiguous_chain():
    _make_table()
    os.environ["AWS_REGION"] = "us-east-1"
    writers = [Ledger(DynamoDBStore(table_name=TABLE, tenant="x")) for _ in range(6)]
    for i, w in enumerate(writers):
        w.append(_pred(f"d{i}"))
    final = Ledger(DynamoDBStore(table_name=TABLE, tenant="x"))
    assert sorted(e.seq for e in final.all()) == [0, 1, 2, 3, 4, 5]
    assert final.verify() is True
