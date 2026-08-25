# Bootstrap: Terraform remote state (native `oci` backend)

Creates the single Object Storage bucket (`documind-tfstate`, versioning
enabled) that holds remote state for every DocuMind environment stack.

## Why the native backend

Since Terraform 1.12 there is a built-in [`oci` backend]
(https://developer.hashicorp.com/terraform/language/backend/oci). Compared to
the older S3-compatible workaround it:

- authenticates with your normal OCI credentials (`config_file_profile`,
  security token, instance principal) — **no Customer Secret Keys**;
- supports **state locking** (lock object in the same bucket);
- stores plain state objects in a normal bucket (easy to inspect/version).

The environment stacks therefore ship an empty `backend "oci" {}` block and
take their configuration from a local, gitignored `backend.hcl`
(see `../environments/demo/README.md`).

## One-time setup

```bash
cd terraform/bootstrap-state
cp terraform.tfvars.example terraform.tfvars   # fill compartment_ocid + region

terraform init
terraform plan
terraform apply
```

Note the `namespace` output, then configure each environment:

```bash
cd ../environments/demo
cp backend.hcl.example backend.hcl             # paste namespace output
terraform init                                 # configures native oci backend
```

## Safety rules

- This stack keeps **local** state on purpose (chicken-and-egg); treat its
  local `terraform.tfstate` as sensitive — it is gitignored.
- Never destroy this stack while any environment still uses the bucket:
  that deletes every environment's state. State cleanup is a separate,
  explicit decision after evidence has been preserved.
