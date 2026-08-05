import argparse
import os
from datahub.ingestion.graph.client import DataHubGraph, DataHubGraphConfig
from datahub.sdk import DataHubClient
from anthropic import Anthropic

# Connections
graph = DataHubGraph(DataHubGraphConfig(server="http://localhost:8080"))
client2 = DataHubClient(server="http://localhost:8080")

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def explain_health_report(dataset_urn, lineage_result, health_issues):
    lineage_summary = str(lineage_result) if lineage_result else "No upstream lineage found."
    health_summary_full = "\n".join(f"- {issue}" for issue in health_issues) or "No issues found."

    prompt = f"""You are a data reliability assistant. Given the following information
about a dataset, write a short, plain-English health report for a non-technical
stakeholder. Be direct about whether the dataset is healthy or not, and if not,
explain the likely cause using the lineage info.

Dataset: {dataset_urn}

Upstream lineage:
{lineage_summary}

Health issues detected:
{health_summary_full}

Write 3-5 sentences max. No jargon like "URN" or "hops" — describe things in plain terms."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
# Parse command-line argument for dataset name/URN
parser = argparse.ArgumentParser(description="Check DataHub dataset health and lineage.")
parser.add_argument("--dataset", required=True, help="Dataset URN to inspect")
args = parser.parse_args()

urn = args.dataset

def write_report_to_datahub(dataset_urn, report_text):
    dataset = client2.entities.get(dataset_urn)
    dataset.set_description(report_text)
    client2.entities.update(dataset)
    print(f"\nWrote report back to DataHub as documentation for {dataset_urn}")

# Fetch entity info
entity = graph.get_entity_raw(urn)
print("DataHub connection test:")
print(entity["urn"])

# Fetch lineage (upstream)
lineage_result = client2.lineage.get_lineage(source_urn=urn, direction="upstream")
print("\nUpstream lineage:")
print(lineage_result)

# Health check: missing documentation or missing owner
description = entity["aspects"].get("editableDatasetProperties", {}).get("value", {}).get("description", "")
has_owner = "ownership" in entity["aspects"]

health_issues = []
if not description:
    health_issues.append("Missing documentation")
if not has_owner:
    health_issues.append("Missing owner")

pii_fields = []
try:
    entity_obj = client2.entities.get(urn)
    for field in entity_obj.schema:
        if field.tags:
            for tag_assoc in field.tags:
                if "PII" in tag_assoc.tag:
                    pii_fields.append(field.field_path)
except Exception:
    pass

if pii_fields:
    health_issues.append(f"Contains PII fields without documented access controls: {', '.join(pii_fields)}")

print("\nHealth check:")
for issue in health_issues:
    print(f"- {issue}")

if not health_issues:
    print("- No issues found")

report = explain_health_report(urn, lineage_result, health_issues)
print("\nPlain-English Health Report:")
print(report)

write_report_to_datahub(urn, report)
