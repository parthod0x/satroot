# SATROOT Examples

This directory contains both runnable ledger examples and reusable preset trees for the higher SATROOT publication layers.

## Quick map

- `genesis_*.json` and `events_*.json` are direct runnable SATROOT ledgers.
- `catalog_presets/` and `stack_presets/` are the first reusable workspace-entry presets.
- `bundle_index_presets/`, `release_catalog_presets/`, and `release_catalog_index_presets/` are the lower signed publication aggregation presets.
- `publication_metadata_catalog_presets/`, `network_presets/`, `publication_catalog_workspace_presets/`, `registry_workspace_presets/`, and `registry_presets/` are the higher publication/discovery presets.

## Lane naming

- `ai_compute_*` is the generic multi-profile lane.
- `machine_compute_*` is the SATROOT-MACHINE-1 lane.
- `stable_reference_*` is the SATROOT-STABLE-1 lane.
- `receipt_invoice_*` is the SATROOT-RECEIPT-1 singleton receipt lane.
- `identity_authority_*` is the SATROOT-IDENTITY-1 singleton identity lane.
- `license_usage_*` is the SATROOT-LICENSE-1 singleton license lane.
- `event_stream_*` is the SATROOT-EVENT-1 single-stream lane; `genesis_event1.json` / `events_event1.json` are its runnable ledger example.

## Collection-backed companions

Several preset directories now include checked-in collection-backed companions for frozen generated artifact sets:

- `catalog_presets/*_collection_backed.json`
- `bundle_index_presets/*_collection_backed.json`
- `release_catalog_presets/*_collection_backed.json`
- `release_catalog_index_presets/*_collection_backed.json`
- `stack_presets/*_collection_backed.json`
- `network_presets/*_collection_backed.json`
- `publication_metadata_catalog_presets/*_collection_backed.json`
- `publication_catalog_workspace_presets/*_collection_backed.json`
- `registry_workspace_presets/*_collection_backed.json`
- `registry_workspace_presets/*_catalog_release_collection_backed.json`
- `registry_presets/*_collection_backed.json`

These collection-backed presets preserve lineage to generated collections such as:

- `bundle_collection_dir`
- `release_collection_dir`
- `release_catalog_collection_dir`
- `catalog_workspace_collection_dir`
- `publication_stack_collection_dir`
- `publication_network_collection_dir`
- `publication_metadata_bundle_collection_dir`
- `publication_catalog_workspace_collection_dir`
- `publication_registry_workspace_collection_dir`

When a CLI command or exported preset points at one of those generated collections, SATROOT accepts either the collection directory itself or the collection `summary.json` and normalizes preserved provenance back to the collection root.

When exported nested presets are also generated, SATROOT keeps those collection references as provenance while using the nested preset tree as the execution input.

## Recommended starting points

If you want the smallest useful preset chain for each lane:

- Generic lower release layers:
  `bundle_index_presets/ai_compute_bundle_index.json`
  `release_catalog_presets/ai_compute_release_stack.json`
  `release_catalog_index_presets/ai_compute_catalog_network.json`
- Generic:
  `catalog_presets/ai_compute_catalog.json`
  `publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog.json`
  `publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace.json`
  `stack_presets/ai_compute_publication_stack.json`
  `network_presets/ai_compute_publication_network.json`
  `registry_workspace_presets/ai_compute_publication_registry_workspace.json`
- Generic collection-backed publication metadata/catalog/stack:
  `catalog_presets/ai_compute_catalog_collection_backed.json`
  `publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace_collection_backed.json`
  `stack_presets/ai_compute_publication_stack_collection_backed.json`
  `registry_workspace_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`

- Machine lower release layers:
  `bundle_index_presets/machine_compute_bundle_index.json`
  `release_catalog_presets/machine_compute_release_stack.json`
  `release_catalog_index_presets/machine_compute_catalog_network.json`
- Machine:
  `catalog_presets/machine_compute_catalog.json`
  `publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog.json`
  `publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace.json`
  `stack_presets/machine_compute_publication_stack.json`
  `network_presets/machine_compute_publication_network.json`
  `registry_workspace_presets/machine_compute_publication_registry_workspace.json`
- Machine collection-backed publication metadata/catalog/stack:
  `catalog_presets/machine_compute_catalog_collection_backed.json`
  `publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace_collection_backed.json`
  `stack_presets/machine_compute_publication_stack_collection_backed.json`
  `registry_workspace_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`

- Stable lower release layers:
  `bundle_index_presets/stable_reference_bundle_index.json`
  `release_catalog_presets/stable_reference_release_stack.json`
  `release_catalog_index_presets/stable_reference_catalog_network.json`
- Stable:
  `catalog_presets/stable_reference_catalog.json`
  `publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog.json`
  `publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace.json`
  `stack_presets/stable_reference_publication_stack.json`
  `network_presets/stable_reference_publication_network.json`
  `registry_workspace_presets/stable_reference_publication_registry_workspace.json`
- Stable collection-backed publication metadata/catalog/stack:
  `catalog_presets/stable_reference_catalog_collection_backed.json`
  `publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace_collection_backed.json`
  `stack_presets/stable_reference_publication_stack_collection_backed.json`
  `registry_workspace_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`

- Singleton reusable catalog-entry presets:
  `catalog_presets/receipt_invoice_catalog.json`
  `catalog_presets/identity_authority_catalog.json`
  `catalog_presets/license_usage_catalog.json`
- Singleton frozen collection-backed catalog-entry presets:
  `catalog_presets/receipt_invoice_catalog_collection_backed.json`
  `catalog_presets/identity_authority_catalog_collection_backed.json`
  `catalog_presets/license_usage_catalog_collection_backed.json`
- Singleton frozen registry-workspace presets:
  `registry_workspace_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json`
  `registry_workspace_presets/identity_authority_publication_registry_workspace_catalog_release_collection_backed.json`
  `registry_workspace_presets/license_usage_publication_registry_workspace_catalog_release_collection_backed.json`
- Singleton frozen top-level registry presets:
  `registry_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json`
  `registry_presets/identity_authority_publication_registry_workspace_catalog_release_collection_backed.json`
  `registry_presets/license_usage_publication_registry_workspace_catalog_release_collection_backed.json`

If you specifically want frozen collection-backed examples, start with:

- `catalog_presets/ai_compute_catalog_collection_backed.json`
- `catalog_presets/machine_compute_catalog_collection_backed.json`
- `catalog_presets/stable_reference_catalog_collection_backed.json`
- `catalog_presets/receipt_invoice_catalog_collection_backed.json`
- `catalog_presets/identity_authority_catalog_collection_backed.json`
- `catalog_presets/license_usage_catalog_collection_backed.json`
- `bundle_index_presets/ai_compute_bundle_index_collection_backed.json`
- `bundle_index_presets/machine_compute_bundle_index_collection_backed.json`
- `bundle_index_presets/stable_reference_bundle_index_collection_backed.json`
- `release_catalog_presets/ai_compute_release_stack_collection_backed.json`
- `release_catalog_presets/machine_compute_release_stack_collection_backed.json`
- `release_catalog_presets/stable_reference_release_stack_collection_backed.json`
- `release_catalog_index_presets/ai_compute_catalog_network_collection_backed.json`
- `release_catalog_index_presets/machine_compute_catalog_network_collection_backed.json`
- `release_catalog_index_presets/stable_reference_catalog_network_collection_backed.json`
- `publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog_collection_backed.json`
- `publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog_collection_backed.json`
- `publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog_collection_backed.json`
- `publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace_collection_backed.json`
- `publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace_collection_backed.json`
- `publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace_collection_backed.json`
- `stack_presets/ai_compute_publication_stack_collection_backed.json`
- `stack_presets/machine_compute_publication_stack_collection_backed.json`
- `stack_presets/stable_reference_publication_stack_collection_backed.json`
- `network_presets/ai_compute_publication_network_collection_backed.json`
- `network_presets/machine_compute_publication_network_collection_backed.json`
- `network_presets/stable_reference_publication_network_collection_backed.json`
- `registry_presets/ai_compute_publication_registry_collection_backed.json`
- `registry_presets/machine_compute_publication_registry_collection_backed.json`
- `registry_presets/stable_reference_publication_registry_collection_backed.json`
- `registry_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/identity_authority_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/license_usage_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json`
- `registry_workspace_presets/machine_compute_publication_registry_workspace_collection_backed.json`
- `registry_workspace_presets/stable_reference_publication_registry_workspace_collection_backed.json`
- `registry_workspace_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/identity_authority_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_workspace_presets/license_usage_publication_registry_workspace_catalog_release_collection_backed.json`

If you want reusable workspace-backed top-level registry presets instead of collection-backed ones, start with:

- `registry_presets/ai_compute_publication_registry_workspace_backed.json`
- `registry_presets/machine_compute_publication_registry_workspace_backed.json`
- `registry_presets/stable_reference_publication_registry_workspace_backed.json`

If you want self-contained frozen-release top-level registry presets that rebuild their own nested registry workspace from a nested collection-backed catalog preset, start with:

- `registry_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- `registry_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`

The checked-in singleton frozen registry presets are also directly reusable once their referenced generated collections exist beside them. A minimal receipt-flavored flow looks like this:

```bash
satroot1 bootstrap-singleton-demo-release-collection --profile SATROOT-RECEIPT-1 --preset-json examples/catalog_presets/receipt_invoice_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir examples/generated_receipt_release_collection_workspace
cp -r examples/generated_receipt_release_collection_workspace/release_collection examples/generated_receipt_release_collection
satroot1 bootstrap-demo-publication-network --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir generated_publication_network
satroot1 bootstrap-publication-network-collection generated_publication_network --output-dir generated_publication_network_collection
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir receipt_frozen_registry_workspace
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --key-id registry-key --output-dir receipt_frozen_registry
```

## Example commands

Build a generic collection-backed bundle index:

```bash
satroot1 build-bundle-index --preset-json examples/bundle_index_presets/ai_compute_bundle_index_collection_backed.json --output bundle_index_collection_backed.json
```

Bootstrap a generic mixed-profile demo release collection from repeated demo-catalog preset inputs:

```bash
satroot1 bootstrap-demo-release-collection --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir demo_release_collection_workspace --label "SATROOT Demo Collection Override"
```

Bootstrap a stable demo release collection from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-release-collection --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir stable_release_collection_workspace --label "SATROOT Stable Collection Override"
```

Bootstrap a machine demo release collection from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-release-collection --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir machine_release_collection_workspace --label "SATROOT Machine Collection Override"
```

Bootstrap a generic mixed-profile demo bundle index workspace from repeated demo-catalog preset inputs:

```bash
satroot1 bootstrap-demo-bundle-index --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --label "SATROOT Demo Bundle Index" --output-dir demo_bundle_index_workspace
```

Bootstrap a stable demo bundle index workspace from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-bundle-index --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --label "Stable Demo Bundle Index" --output-dir stable_bundle_index_workspace
```

Bootstrap a machine demo bundle index workspace from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-bundle-index --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --label "Machine Demo Bundle Index" --output-dir machine_bundle_index_workspace
```

Bootstrap a stable demo release catalog publication from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-release-catalog-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Stable Collection Override" --label "Stable Demo Release Catalog" --output-dir stable_demo_release_catalog_publication
```

Bootstrap a machine demo release catalog publication from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-release-catalog-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Machine Collection Override" --label "Machine Demo Release Catalog" --output-dir machine_demo_release_catalog_publication
```

Bootstrap a generic mixed-profile demo release catalog publication from repeated demo-catalog preset inputs:

```bash
satroot1 bootstrap-demo-release-catalog-publication --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "SATROOT Demo Collection Override" --label "SATROOT Demo Release Catalog" --output-dir demo_release_catalog_publication
```

Bootstrap a stable demo release catalog index publication from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-release-catalog-index-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Stable Demo Release Catalog" --label "Stable Demo Release Catalog Index" --output-dir stable_demo_release_catalog_index_publication
```

Bootstrap a machine demo release catalog index publication from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-release-catalog-index-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Machine Demo Release Catalog" --label "Machine Demo Release Catalog Index" --output-dir machine_demo_release_catalog_index_publication
```

Bootstrap a generic mixed-profile demo release catalog index publication from repeated demo-catalog preset inputs:

```bash
satroot1 bootstrap-demo-release-catalog-index-publication --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "SATROOT Demo Release Catalog" --label "SATROOT Demo Release Catalog Index" --output-dir demo_release_catalog_index_publication
```

Bootstrap a stable demo publication stack from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-publication-stack --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Stable Demo Publication Stack" --output-dir stable_demo_publication_stack
```

Bootstrap a generic mixed-profile demo publication stack from repeated preset inputs:

```bash
satroot1 bootstrap-demo-publication-stack --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "SATROOT Demo Publication Stack" --output-dir demo_publication_stack
```

Bootstrap a machine demo publication stack from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-publication-stack --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Machine Demo Publication Stack" --output-dir machine_demo_publication_stack
```

Bootstrap a singleton receipt release collection from repeated singleton receipt preset inputs:

```bash
satroot1 bootstrap-singleton-demo-release-collection --profile SATROOT-RECEIPT-1 --preset-json examples/catalog_presets/receipt_invoice_catalog.json --preset-json examples/catalog_presets/receipt_invoice_catalog.json --scheme hmac-sha256 --release-key-id release-key --label "Receipt Collection Override" --output-dir receipt_release_collection_workspace
```

Bootstrap a singleton identity publication network from repeated singleton identity preset inputs:

```bash
satroot1 bootstrap-singleton-demo-publication-network --profile SATROOT-IDENTITY-1 --preset-json examples/catalog_presets/identity_authority_catalog.json --preset-json examples/catalog_presets/identity_authority_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Identity Authority Stack" --label "Identity Authority Network" --output-dir identity_publication_network_workspace
```

Bootstrap a singleton license publication registry workspace from repeated singleton license preset inputs:

```bash
satroot1 bootstrap-singleton-demo-publication-registry-workspace --profile SATROOT-LICENSE-1 --preset-json examples/catalog_presets/license_usage_catalog.json --preset-json examples/catalog_presets/license_usage_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --publication-registry-label "License Usage Registry" --output-dir license_publication_registry_workspace
```

Bootstrap a stable demo publication network from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-publication-network --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Stable Demo Publication Stack" --label "Stable Demo Publication Network" --output-dir stable_demo_publication_network
```

Bootstrap a generic mixed-profile demo publication network from repeated preset inputs:

```bash
satroot1 bootstrap-demo-publication-network --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "SATROOT Demo Publication Stack" --label "SATROOT Demo Publication Network" --output-dir demo_publication_network
```

Bootstrap a machine demo publication network from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-publication-network --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Machine Demo Publication Stack" --label "Machine Demo Publication Network" --output-dir machine_demo_publication_network
```

Bootstrap a stable demo publication catalog workspace from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-publication-catalog-workspace --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "Stable Demo Catalog Release Override" --descriptor-index-label "Stable Demo Workspace Descriptor Index" --publication-metadata-catalog-label "Stable Demo Workspace Metadata Catalog" --output-dir stable_demo_publication_catalog_workspace
```

Bootstrap a generic mixed-profile demo publication catalog workspace from repeated preset inputs:

```bash
satroot1 bootstrap-demo-publication-catalog-workspace --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "SATROOT Demo Catalog Release Override" --descriptor-index-label "SATROOT Demo Workspace Descriptor Index" --publication-metadata-catalog-label "SATROOT Demo Workspace Metadata Catalog" --output-dir demo_publication_catalog_workspace
```

Bootstrap a machine demo publication catalog workspace from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-publication-catalog-workspace --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "Machine Demo Catalog Release Override" --descriptor-index-label "Machine Demo Workspace Descriptor Index" --publication-metadata-catalog-label "Machine Demo Workspace Metadata Catalog" --output-dir machine_demo_publication_catalog_workspace
```

Bootstrap a stable demo publication registry workspace from repeated stable preset inputs:

```bash
satroot1 bootstrap-stable-demo-publication-registry-workspace --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "Stable Demo Registry Release Override" --release-catalog-label "Stable Demo Registry Publication Stack" --release-catalog-index-label "Stable Demo Registry Publication Network" --descriptor-index-label "Stable Demo Registry Descriptor Index" --publication-metadata-catalog-label "Stable Demo Registry Metadata Catalog" --publication-registry-label "Stable Demo Publication Registry" --output-dir stable_demo_publication_registry_workspace
```

Bootstrap a generic mixed-profile demo publication registry workspace from repeated preset inputs:

```bash
satroot1 bootstrap-demo-publication-registry-workspace --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "SATROOT Demo Registry Release Override" --release-catalog-label "SATROOT Demo Registry Publication Stack" --release-catalog-index-label "SATROOT Demo Registry Publication Network" --descriptor-index-label "SATROOT Demo Registry Descriptor Index" --publication-metadata-catalog-label "SATROOT Demo Registry Metadata Catalog" --publication-registry-label "SATROOT Demo Publication Registry" --output-dir demo_publication_registry_workspace
```

Bootstrap a machine demo publication registry workspace from repeated machine preset inputs:

```bash
satroot1 bootstrap-machine-demo-publication-registry-workspace --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "Machine Demo Registry Release Override" --release-catalog-label "Machine Demo Registry Publication Stack" --release-catalog-index-label "Machine Demo Registry Publication Network" --descriptor-index-label "Machine Demo Registry Descriptor Index" --publication-metadata-catalog-label "Machine Demo Registry Metadata Catalog" --publication-registry-label "Machine Demo Publication Registry" --output-dir machine_demo_publication_registry_workspace
```

Bootstrap a machine collection-backed release catalog publication:

```bash
satroot1 bootstrap-machine-release-catalog-publication --preset-json examples/release_catalog_presets/machine_compute_release_stack_collection_backed.json --output-dir machine_release_catalog_collection_backed --label "SATROOT Machine Collection-Backed Release Stack Override" --scheme hmac-sha256 --key-id catalog-key
```

Bootstrap a stable collection-backed release catalog index publication:

```bash
satroot1 bootstrap-stable-release-catalog-index-publication --preset-json examples/release_catalog_index_presets/stable_reference_catalog_network_collection_backed.json --output-dir stable_release_catalog_index_collection_backed --label "SATROOT Stable Collection-Backed Catalog Network Override" --scheme hmac-sha256 --key-id index-key
```

Bootstrap a generic publication network from a checked-in network preset:

```bash
satroot1 bootstrap-publication-network --network-preset-json examples/network_presets/ai_compute_publication_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir publication_network --label "SATROOT Network Override"
```

Bootstrap a generic collection-backed publication network:

```bash
satroot1 bootstrap-publication-network --network-preset-json examples/network_presets/ai_compute_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir publication_network_collection_backed --label "SATROOT Collection-Backed Network Override"
```

Bootstrap a generic collection-backed publication stack:

```bash
satroot1 bootstrap-publication-stack --stack-preset-json examples/stack_presets/ai_compute_publication_stack_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir publication_stack_collection_backed --label "SATROOT Collection-Backed Stack Override"
```

Bootstrap a generic collection-backed publication metadata catalog publication:

```bash
satroot1 bootstrap-publication-metadata-catalog-publication --preset-json examples/publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog_collection_backed.json --output-dir publication_metadata_catalog_collection_backed --scheme hmac-sha256 --key-id catalog-key --label "SATROOT Collection-Backed Metadata Catalog Override"
```

Bootstrap a generic collection-backed publication catalog workspace:

```bash
satroot1 bootstrap-publication-catalog-workspace --preset-json examples/publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir publication_catalog_workspace_collection_backed
```

Bootstrap a generic collection-backed registry workspace:

```bash
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_collection_backed
```

Bootstrap a generic frozen-release collection-backed registry workspace directly from a self-contained registry-workspace preset:

```bash
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_frozen_catalog
```

Freeze multiple generated publication catalog workspaces into one reusable collection:

```bash
satroot1 bootstrap-publication-catalog-workspace-collection generated_publication_catalogs/catalog_alpha generated_publication_catalogs/catalog_beta --output-dir publication_catalog_workspace_collection
```

Freeze multiple generated publication registry workspaces into one reusable collection:

```bash
satroot1 bootstrap-publication-registry-workspace-collection generated_publication_registries/registry_alpha generated_publication_registries/registry_beta --output-dir publication_registry_workspace_collection
```

Bootstrap a machine collection-backed publication network:

```bash
satroot1 bootstrap-machine-publication-network --network-preset-json examples/network_presets/machine_compute_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir machine_publication_network_collection_backed --label "SATROOT Machine Collection-Backed Network Override"
```

Bootstrap a machine collection-backed registry workspace:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --preset-json examples/registry_workspace_presets/machine_compute_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_collection_backed
```

Bootstrap a machine frozen-release collection-backed registry workspace directly from a self-contained registry-workspace preset:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --preset-json examples/registry_workspace_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_frozen_catalog
```

Bootstrap a stable collection-backed publication network:

```bash
satroot1 bootstrap-stable-publication-network --network-preset-json examples/network_presets/stable_reference_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir stable_publication_network_collection_backed --label "SATROOT Stable Collection-Backed Network Override"
```

Bootstrap a stable collection-backed registry workspace:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --preset-json examples/registry_workspace_presets/stable_reference_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_collection_backed
```

Bootstrap a stable frozen-release collection-backed registry workspace directly from a self-contained registry-workspace preset:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --preset-json examples/registry_workspace_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_frozen_catalog
```

Bootstrap a generic workspace-backed top-level registry publication:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_workspace_backed.json --output-dir publication_registry_publication_workspace_backed --label "SATROOT Workspace-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a generic collection-backed top-level registry publication:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_collection_backed.json --output-dir publication_registry_publication_collection_backed --label "SATROOT Collection-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a generic frozen-release collection-backed top-level registry publication directly from a self-contained registry preset:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json --output-dir publication_registry_publication_frozen_catalog --label "SATROOT Frozen Catalog Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a machine workspace-backed top-level registry publication:

```bash
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_workspace_backed.json --output-dir machine_publication_registry_publication_workspace_backed --label "SATROOT Machine Workspace-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a stable workspace-backed top-level registry publication:

```bash
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_workspace_backed.json --output-dir stable_publication_registry_publication_workspace_backed --label "SATROOT Stable Workspace-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a stable collection-backed top-level registry publication:

```bash
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_collection_backed.json --output-dir stable_publication_registry_publication_collection_backed --label "SATROOT Stable Collection-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a machine collection-backed top-level registry publication:

```bash
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_collection_backed.json --output-dir machine_publication_registry_publication_collection_backed --label "SATROOT Machine Collection-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap machine and stable frozen-release collection-backed top-level registry publications directly from their self-contained registry presets:

```bash
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json --output-dir machine_publication_registry_publication_frozen_catalog --label "SATROOT Machine Frozen Catalog Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json --output-dir stable_publication_registry_publication_frozen_catalog --label "SATROOT Stable Frozen Catalog Registry Override" --scheme hmac-sha256 --key-id registry-key
```
