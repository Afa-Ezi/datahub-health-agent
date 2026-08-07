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


def write_report_to_datahub(dataset_urn, report_text):
    dataset = client2.entities.get(dataset_urn)
    dataset.set_description(report_text)
    client2.entities.update(dataset)
    print(f"\nWrote report back to DataHub as documentation for {dataset_urn}")


def analyze_dataset(urn):
    """Runs the full health check pipeline on a single dataset URN."""
    try:
        entity = graph.get_entity_raw(urn)
    except Exception as e:
        print(f"\nCould not fetch dataset {urn}: {e}")
        return

    print("\nDataHub connection test:")
    print(entity["urn"])

    # Fetch lineage (upstream)
    try:
        lineage_result = client2.lineage.get_lineage(source_urn=urn, direction="upstream")
    except Exception:
        lineage_result = []
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


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Check DataHub dataset health and lineage.")
parser.add_argument("--dataset", help="Dataset URN to inspect")
parser.add_argument("--scan-all", action="store_true", help="Scan all datasets in DataHub")
parser.add_argument("--limit", type=int, default=None, help="Limit number of datasets when using --scan-all")
args = parser.parse_args()

if not args.dataset and not args.scan_all:
    parser.error("Provide either --dataset <urn> or --scan-all")

if args.scan_all:
    print("Scanning all datasets in DataHub...")
    all_urns = list(graph.get_urns_by_filter(entity_types=["dataset"]))
    if args.limit:
        all_urns = all_urns[:args.limit]
    print(f"Found {len(all_urns)} datasets to process.\n")
    for i, dataset_urn in enumerate(all_urns, start=1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(all_urns)}] Analyzing: {dataset_urn}")
        print(f"{'='*60}")
        analyze_dataset(dataset_urn)
else:
    analyze_dataset(args.dataset)
