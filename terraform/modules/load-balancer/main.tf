# DocuMind AI — Load Balancer Module
# Public LB for routing traffic to OKE services

resource "oci_load_balancer_load_balancer" "main" {
  compartment_id = var.compartment_id
  display_name   = "${var.name_prefix}-lb"
  shape          = var.lb_shape

  dynamic "shape_details" {
    for_each = var.lb_shape == "flexible" ? [1] : []
    content {
      minimum_bandwidth_in_mbps = var.lb_min_bandwidth
      maximum_bandwidth_in_mbps = var.lb_max_bandwidth
    }
  }

  subnet_ids                 = [var.subnet_lb_id]
  network_security_group_ids = [var.nsg_lb_id]
  is_private                 = false

  freeform_tags = var.tags
}

# ---------- Backend Set ----------
resource "oci_load_balancer_backend_set" "api" {
  load_balancer_id = oci_load_balancer_load_balancer.main.id
  name             = "${var.name_prefix}-bs-api"
  policy           = "ROUND_ROBIN"

  health_checker {
    protocol          = "HTTP"
    port              = var.backend_port
    url_path          = var.health_check_path
    interval_ms       = 10000
    timeout_in_millis = 3000
    retries           = 3
    return_code       = 200
  }

  session_persistence_configuration {
    cookie_name      = "DOCUMIND_LB"
    disable_fallback = false
  }
}

# ---------- Backends (placeholder — populated by OKE/Ingress) ----------
# Note: When using OKE with LoadBalancer-type Services or Ingress controllers,
# backends are managed automatically. These are placeholder resources for
# manual backend registration if needed.
resource "oci_load_balancer_backend" "api_nodes" {
  for_each = var.backend_ips

  load_balancer_id = oci_load_balancer_load_balancer.main.id
  backendset_name  = oci_load_balancer_backend_set.api.name
  ip_address       = each.value
  port             = var.backend_port
  weight           = 1
}

# ---------- Listener: HTTP ----------
resource "oci_load_balancer_listener" "http" {
  load_balancer_id         = oci_load_balancer_load_balancer.main.id
  name                     = "${var.name_prefix}-listener-http"
  default_backend_set_name = oci_load_balancer_backend_set.api.name
  port                     = 80
  protocol                 = "HTTP"

  connection_configuration {
    idle_timeout_in_seconds = 60
  }
}

# ---------- Listener: HTTPS (optional) ----------
resource "oci_load_balancer_listener" "https" {
  count = var.ssl_certificate_id != "" ? 1 : 0

  load_balancer_id         = oci_load_balancer_load_balancer.main.id
  name                     = "${var.name_prefix}-listener-https"
  default_backend_set_name = oci_load_balancer_backend_set.api.name
  port                     = 443
  protocol                 = "HTTP"

  ssl_configuration {
    certificate_ids         = [var.ssl_certificate_id]
    verify_peer_certificate = false
    protocols               = ["TLSv1.2", "TLSv1.3"]
  }

  connection_configuration {
    idle_timeout_in_seconds = 60
  }
}
