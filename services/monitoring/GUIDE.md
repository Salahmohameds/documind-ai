# Adding a new service to observability

## 1. Requirements

Add the requirements in `services/monitoring/requirements.txt` to the service's requirements file.

## 2. Your app code

Use the 3 files in `services/monitoring/app_instrumentation` in your service to import the following dependencies:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from app_instrumentation.logging_setup import configure_logging
from app_instrumentation.otel_setup import setup_tracing, setup_metrics
from app_instrumentation.request_id_middleware import RequestIDMiddleware, get_request_id
```

Then modify your FastAPI app as follows:

```python
app = FastAPI()

logger = configure_logging(service_name=SERVICE_NAME)
setup_tracing(app, service_name=SERVICE_NAME)
setup_metrics(app)
app.add_middleware(RequestIDMiddleware)
RequestsInstrumentor().instrument()
```

Full example in `services/monitoring/sample_app.py`

## 3. Kubernetes

Modify your service deployment `<your-service>.yaml` file as follows:

Add this environment variable in your service deployment:

```yaml
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "otel-collector.monitoring.svc.cluster.local:4317"
```

Then add this part at the bottom of your deployment file:

```yaml
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: <service-name>
  namespace: <namespace-name-of-said-service>
  labels:
    release: kube-prom-stack
spec:
  selector:
    matchLabels:
      app: <service-name>
  endpoints:
    - port: <name-of-service-port>
      path: /metrics
      interval: 15s
```

Modify the placeholders as required:
- `<service-name>`: The name of your service.
- `<namespace-name-of-said-service>`: The namespace your service exists in.
- `<name-of-service-port>` NOT the port number, but the name of the port. Requires you to give your port a name.

Then finally, apply the changes:

```bash
kubectl apply -f <your-service>.yaml
```

## 4. Logger

Instead of using your own logic for logging, please use the `logger` you created with the `configure_logging` function. This allows Grafana to capture any expected errors from the services.

Example for `logger.info`:

```python
logger.info("order created", extra={"order_id": order_id, "user_id": user_id})
```

Example for `logger.error`:

```python
logger.error("payment failed", extra={"order_id": order_id, "reason": str(e)})
```

## 5. Deployment (CLOUD ADMIN ONLY)

Once you have the configuration files from `kubernetes/monitoring`, please execute these commands in this exact order:

```bash
kubectl apply -f monitoring-namespace.yaml

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm repo update

helm install kube-prom-stack prometheus-community/kube-prometheus-stack -n monitoring -f kube-prometheus-stack-values.yaml

kubectl apply -f otel-collector.yaml

kubectl apply -f jaeger.yaml

kubectl apply -f grafana-dashboard-configmap.yaml

kubectl rollout restart deployment -n monitoring kube-prom-stack-grafana
```

Now all you need is to expose Grafana so you can access it from your browser. We can do this by modifying the Grafana service to use a `LoadBalancer` for example (we should not expose a Load Balancer specifically for Grafana, but this is just a demonstration on how to expose a public IP):

```bash
kubectl patch svc kube-prom-stack-grafana -n monitoring -p '{"spec":{"type":"LoadBalancer"}}'
```

## 6. Dashboard (CLOUD ADMIN ONLY)

Once Grafana is publicly reachable, execute:

```bash
kubectl get svc -n monitoring kube-prom-stack-grafana
```

to find the `EXTERNAL-IP`. The port is configured to `80` so you can just directly visit the `EXTERNAL-IP` on your browser.

### Grafana login

Credentials will be shared privately.