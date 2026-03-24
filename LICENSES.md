# Licenses

## Code

All code in this repository is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE).

## Output Data

The processed data in `output/` is derived from third-party sources. Each source has its own license that governs use of the derived data. Our tiling, enrichment, and curation work is licensed under **CC-BY-SA 4.0**, but the underlying data retains its original license terms.

**You must comply with the most restrictive applicable license for each globe's data.**

### Per-globe data sources

| Globe | Source | License | Commercial Use | Requirements |
|-------|--------|---------|----------------|-------------|
| Fish | FishBase | CC-BY-NC 4.0 | No | Credit FishBase |
| Fish | GBIF | CC0 / CC-BY 4.0 | Varies by record | Credit GBIF; check individual records |
| Dino | Paleobiology Database (PBDB) | CC-BY 4.0 | Yes | Credit PBDB |
| Volcano | Smithsonian GVP | CC-BY-NC 4.0 | No | Credit Smithsonian Global Volcanism Program |
| Quake | USGS | Public domain | Yes | No requirements (credit appreciated) |
| Meteor | NASA | Public domain | Yes | No requirements (credit appreciated) |
| Shipwreck | NOAA AWOIS | Public domain | Yes | No requirements (credit appreciated) |
| Bird | GBIF (includes eBird) | CC0 / CC-BY 4.0 | Varies by record | Credit GBIF |
| Satellite | CelesTrak | Public domain | Yes | No requirements (credit appreciated) |
| Aquatic | OBIS | CC-BY 4.0 | Yes | Credit OBIS |
| Aquatic | FishBase | CC-BY-NC 4.0 | No | Credit FishBase |

### What this means for you

- **Non-commercial globes** (Fish, Volcano): data includes CC-BY-NC sources. You may share and adapt, but not for commercial purposes. You must give credit.
- **Commercial-OK globes** (Dino, Quake, Meteor, Shipwreck): data is CC-BY or public domain. You may use commercially with attribution.
- **Mixed globes** (Bird, Aquatic): individual records may have different licenses. Check GBIF record-level licensing.

### Attribution

Each globe's `index.json` includes an `attribution` array with the required credits for display. Globe frontends render this via the Attribution component.
