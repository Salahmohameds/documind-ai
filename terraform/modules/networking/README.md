# Networking module

Creates the complete DocuMind network fabric:

| Piece | Detail |
|---|---|
| VCN | Single CIDR, DNS-enabled |
| Gateways | IGW (public), NAT (private egress), SGW optional (Oracle Services Network) |
| Subnets | `for_each` over a map: `public_lb`, `oke_api`, `oke_workers`, `oke_pods` (VCN-native CNI), `data`, optional `bastion` |
| Route tables | One per subnet; `igw`/`nat`/`none` default route + private OSN route via SGW |
| Security lists | Per-subnet profiles (`public_lb`, `private_oke`, `data`, `bastion`, `locked`) as subnet defaults only |
| NSGs | Workload-level control: `lb`, `oke_api`, `workers`, `pods`, `data`; every rule data-driven with a description |
| Flow logs | Optional per-subnet flow logs behind `enable_flow_logs` |

## Inputs / outputs

See `variables.tf` and `outputs.tf`. Notable validations:

- every subnet CIDR must sit inside `vcn_cidr`;
- subnet CIDRs must not overlap each other;
- `admin_cidrs` must not contain `0.0.0.0/0` — the Kubernetes API is never world-open.

## Example

```hcl
module "networking" {
  source       = "../../modules/networking"
  name_prefix  = "dm-demo"
  admin_cidrs  = ["203.0.113.7/32"]
  subnets = {
    public_lb   = { cidr = "10.20.1.0/24",   dns_label = "publb",      private = false, route = "igw",  enable_logs = true }
    oke_api     = { cidr = "10.20.2.0/28",   dns_label = "okeapi",     private = false, route = "igw" }
    oke_workers = { cidr = "10.20.10.0/24",  dns_label = "okeworkers", private = true,  route = "nat" }
    oke_pods    = { cidr = "10.20.64.0/18",  dns_label = "okepods",    private = true,  route = "nat" }
    data        = { cidr = "10.20.30.0/24",  dns_label = "data",       private = true,  route = "none" }
  }
}
```

## Notes

- The pod subnet defaults to `/18`: VCN-native pod networking assigns each pod
  a real VCN IP (~31 per node by default); `/24` exhausts quickly.
- The `oke_api` subnet is dedicated to the Kubernetes endpoint. Its route type
  follows the cluster's endpoint mode: IGW-routed when the endpoint is public,
  NAT-routed for a private endpoint.
- Redis runs in-cluster (pod), so no Redis rules exist on `data`; pod-to-pod
  traffic is governed by Kubernetes NetworkPolicies.
