# OKE module

Creates the OKE cluster and `for_each`-driven node pools on VCN-native pod
networking with private workers.

## Key decisions baked in

| Decision | Rationale |
|---|---|
| Dedicated `endpoint_subnet_id` | The API endpoint is never parked inside the worker subnet (master design requirement) |
| Per-pool NSG separation | Workers, pods, endpoint each get their own security identity |
| `node_pools` map | Add/remove/scale pools via configuration only; addresses stay stable |
| Image auto-resolution | Newest Oracle-Linux-OKE image matching the effective Kubernetes version + pool CPU arch; explicit `node_image_id` always wins |
| ENHANCED_CLUSTER option | Required for OKE Workload Identity; BASIC stays default for cost |
| Preconditions | Fail fast on empty version/image/subnets before any OCI call creates half a cluster |

## Example

```hcl
module "oke" {
  source = "../../modules/oke"

  name_prefix        = "dm-demo"
  kubernetes_version = ""                # latest offered
  node_pools = {
    apps    = { size = 1, shape = "VM.Standard.E4.Flex", ocpus = 2, memory_in_gbs = 8 }
    batch   = { size = 1, shape = "VM.Standard.A1.Flex", ocpus = 2, memory_in_gbs = 8, labels = { workload = "batch" } }
  }
}
```

## Notes

- Pod subnet sizing: VCN-native CNI burns a VCN IP per pod (~31/node);
  size the pod subnet `/18` or larger.
- SSH is optional; prefer leaving `ssh_public_key` empty and using OCI
  Bastion + session-based access when debugging is needed.
