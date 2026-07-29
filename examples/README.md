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

## Collection-backed companions

Several preset directories now include checked-in collection-backed companions for frozen generated artifact sets:

- `bundle_index_presets/*_collection_backed.json`
- `release_catalog_presets/*_collection_backed.json`
- `release_catalog_index_presets/*_collection_backed.json`
- `stack_presets/*_collection_backed.json`
- `network_presets/*_collection_backed.json`
- `publication_metadata_catalog_presets/*_collection_backed.json`
- `publication_catalog_workspace_presets/*_collection_backed.json`
- `registry_workspace_presets/*_collection_backed.json`
- `registry_presets/*_collection_backed.json`

These collection-backed presets preserve lineage to generated collections such as:

- `bundle_collection_dir`
- `release_collection_dir`
- `release_catalog_collection_dir`
- `catalog_workspace_collection_dir`
- `publication_stack_collection_dir`
- `publication_network_collection_dir`
- `publication_metadata_bundle_collection_dir`
- `publication_registry_workspace_dir`

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
  `publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace_collection_backed.json`
  `stack_presets/ai_compute_publication_stack_collection_backed.json`

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
  `publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace_collection_backed.json`
  `stack_presets/machine_compute_publication_stack_collection_backed.json`

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
  `publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog_collection_backed.json`
  `publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace_collection_backed.json`
  `stack_presets/stable_reference_publication_stack_collection_backed.json`

If you specifically want frozen collection-backed examples, start with:

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
- `registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json`
- `registry_workspace_presets/machine_compute_publication_registry_workspace_collection_backed.json`
- `registry_workspace_presets/stable_reference_publication_registry_workspace_collection_backed.json`

If you want reusable workspace-backed top-level registry presets instead of collection-backed ones, start with:

- `registry_presets/ai_compute_publication_registry_workspace_backed.json`
- `registry_presets/machine_compute_publication_registry_workspace_backed.json`
- `registry_presets/stable_reference_publication_registry_workspace_backed.json`

## Example commands

Build a generic collection-backed bundle index:

```bash
satroot1 build-bundle-index --preset-json examples/bundle_index_presets/ai_compute_bundle_index_collection_backed.json --output bundle_index_collection_backed.json
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
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_collection_backed --publication-registry-label "SATROOT Collection-Backed Registry Override"
```

Bootstrap a machine collection-backed publication network:

```bash
satroot1 bootstrap-machine-publication-network --network-preset-json examples/network_presets/machine_compute_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir machine_publication_network_collection_backed --label "SATROOT Machine Collection-Backed Network Override"
```

Bootstrap a machine collection-backed registry workspace:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --catalog-preset-json examples/catalog_presets/machine_compute_catalog.json --publication-catalog-workspace-preset-json examples/publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace.json --preset-json examples/registry_workspace_presets/machine_compute_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_collection_backed --publication-registry-label "SATROOT Machine Collection-Backed Registry Override"
```

Bootstrap a stable collection-backed publication network:

```bash
satroot1 bootstrap-stable-publication-network --network-preset-json examples/network_presets/stable_reference_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir stable_publication_network_collection_backed --label "SATROOT Stable Collection-Backed Network Override"
```

Bootstrap a stable collection-backed registry workspace:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --catalog-preset-json examples/catalog_presets/stable_reference_catalog.json --publication-catalog-workspace-preset-json examples/publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace.json --preset-json examples/registry_workspace_presets/stable_reference_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_collection_backed --publication-registry-label "SATROOT Stable Collection-Backed Registry Override"
```

Bootstrap a generic workspace-backed top-level registry publication:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_workspace_backed.json --output-dir publication_registry_publication_workspace_backed --label "SATROOT Workspace-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
```

Bootstrap a generic collection-backed top-level registry publication:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_collection_backed.json --output-dir publication_registry_publication_collection_backed --label "SATROOT Collection-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
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
