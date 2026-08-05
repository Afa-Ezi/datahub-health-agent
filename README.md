# datahub-health-agent

An agent that checks a dataset's health in DataHub — missing documentation, missing ownership — traces its upstream lineage to show what feeds into it, explains the findings in plain English, and writes that report back into DataHub as documentation so the next person (or agent) who looks at the dataset immediately sees its status.

Built for the **DataHub Agent Hackathon 2026**, category: *Agents That Do Real Work*.

## What it does

Given a dataset URN, the agent:
1. Connects to a local DataHub instance and fetches the dataset's metadata
2. Traces its upstream lineage (what job or table feeds this dataset)
3. Checks for missing documentation, missing ownership, and PII fields without documented access controls
4. Generates a plain-English health report combining all of the above
5. **Writes that report back into DataHub** as the dataset's documentation — so the finding is inherited by the next person or agent that opens the dataset, not lost in a terminal window

## Example usage

```bash
python3 agent.py --dataset "urn:li:dataset:(urn:li:dataPlatform:s3,b2fd91.demo-data-bucket/order_entry/orders,PROD)"
```

Example output:

```
DataHub connection test:
urn:li:dataset:(urn:li:dataPlatform:s3,b2fd91.demo-data-bucket/order_entry/orders,PROD)

Upstream lineage:
[LineageResult(... name='export_table_orders_to_s3' ...)]

Health check:
- Missing owner

Plain-English Health Report:
This dataset (b2fd91.demo-data-bucket/order_entry/orders) currently has the
following problems: Missing owner. Tracing its lineage shows it depends on
one upstream job (export_table_orders_to_s3). Because of missing owner,
it's hard for anyone on the team to know who's responsible for this data
or what it's supposed to contain.

Wrote report back to DataHub as documentation for urn:li:dataset:(...)
```

## Setup

1. Install and start DataHub locally:
```bash
   pip install acryl-datahub --break-system-packages
   datahub docker quickstart
   datahub init --username datahub --password datahub
   datahub datapack load showcase-ecommerce
```
2. Install dependencies:
```bash
   pip install anthropic --break-system-packages
```
3. Set your Anthropic API key (optional — see Known Limitations below):
```bash
   export ANTHROPIC_API_KEY=your_key_here
```
4. Run the agent against any dataset URN in your DataHub instance:
```bash
   python3 agent.py --dataset "<urn>"
```

## What DataHub features this uses

- **DataHub Python SDK** (`datahub.sdk.DataHubClient`) — fetching lineage, reading/writing dataset entities
- **DataHub Graph client** (`DataHubGraph`) — reading raw entity aspects (documentation, ownership)
- **Write-back** — using `entities.get()` / `set_description()` / `entities.update()` to persist the generated report as the dataset's documentation

## Known limitations

- **LLM explanation step currently uses a template**, not a live Claude API call, due to API billing setup — the real API integration is implemented in `agent.py` (see the commented-out block in `explain_health_report`) and can be enabled by uncommenting it once `ANTHROPIC_API_KEY` has credit.
- **Ownership check reflects direct dataset-level ownership only.** Some datasets show owners in the DataHub UI that are inherited from a parent container or domain rather than attached directly to the dataset — this agent currently only detects direct, dataset-level ownership records.
- **Single dataset at a time.** A "scan all datasets" mode was considered as a stretch goal but wasn't built due to time constraints.
- **Write-back overwrites existing documentation** rather than appending to it — running the agent on a dataset that already has real documentation will replace it with the generated report.

## What's next

- Enable the real Claude API call for richer, more varied explanations
- Add a "scan all datasets" mode
- Detect inherited/domain-level ownership in addition to direct ownership
- Append to existing documentation instead of overwriting it
