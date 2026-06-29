# Lambda entrypoint for the EventBridge-driven resolution loop.
# Processes EVERY registered tenant — settlement is autonomous and multi-tenant.
from forward_ledger import Ledger, build_store, calibration, list_tenants, resolve_due
from forward_ledger.oracles import HttpOracle, polymarket_resolver


def handler(event, context):
    oracle = HttpOracle({"polymarket:": polymarket_resolver})
    results = []
    for tenant in list_tenants():
        try:
            lg = Ledger(build_store(tenant=tenant))
            settled = resolve_due(lg, oracle)
            results.append({"tenant": tenant, "settled": len(settled),
                            "forward_resolved": calibration(lg)["forward"]["n"],
                            "chain_valid": lg.verify()})
        except Exception as ex:   # one tenant failing must not block the others
            results.append({"tenant": tenant, "error": str(ex)})
    return {"tenants": len(results),
            "settled_total": sum(r.get("settled", 0) for r in results),
            "results": results}
