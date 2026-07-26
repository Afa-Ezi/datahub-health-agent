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
    # TEMPORARY STUB — replace with real Anthropic API call once billing is set up
    # Real version is commented out below for later

    health_summary = ", ".join(health_issues) if health_issues else "no issues"
    if lineage_result:
        job_name = lineage_result[0].name or "an unnamed job"
        lineage_note = f"one upstream job ({job_name})"
    else:
        lineage_note = "no upstream lineage"
    return (
        f"This dataset ({dataset_urn.split(',')[1]}) currently has the following problems: "
        f"{health_summary}. Tracing its lineage shows it depends on {lineage_note}. "
        f"Because of {health_summary.lower()}, it's hard for anyone on the team "
        f"to know who's responsible for this data or what it's supposed to contain."
    )

    # --- Real version (uncomment once you have API credit) ---
    # lineage_summary = str(lineage_result) if lineage_result else "No upstream lineage found."
    # health_summary_full = "\n".join(f"- {issue}" for issue in health_issues) or "No issues found."
    # prompt = f"""You are a data reliability assistant...
    # (full prompt as before)
    # """
    # response = client.messages.create(
    #     model="claude-sonnet-4-6",
    #     max_tokens=300,
    #     messages=[{"role": "user", "content": prompt}]
    # )
    # return response.content[0].text

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

print("\nHealth check:")
for issue in health_issues:
    print(f"- {issue}")

if not health_issues:
    print("- No issues found")

report = explain_health_report(urn, lineage_result, health_issues)
print("\nPlain-English Health Report:")
print(report)

write_report_to_datahub(urn, report)
