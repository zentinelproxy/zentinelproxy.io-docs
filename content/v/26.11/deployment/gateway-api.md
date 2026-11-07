+++
title = "Gateway API Controller"
weight = 6
description = "Run Zentinel as a Kubernetes Gateway API implementation with the zentinel-gateway controller."
+++

`zentinel-gateway` is a Kubernetes controller that implements the [Gateway API](https://gateway-api.sigs.k8s.io/). It watches Gateway API resources (and `Ingress` objects of class `zentinel`), translates them into a Zentinel configuration, and hands that configuration to a Zentinel proxy running next to it.

{% callout(type="warning", title="Early-stage implementation") %}
The controller covers the core HTTP routing path and is still working towards full Gateway API conformance. The latest published conformance report fails 2 of 33 core `GATEWAY-HTTP` tests, and several resources are accepted without being programmed into the data plane. Read [Limitations](#limitations) before using it in production. For full control over the proxy configuration, deploy Zentinel with the [Helm chart or plain manifests](../kubernetes/) instead.
{% end %}

## How it works

The Helm chart runs one pod with two containers:

| Container | Image | Role |
|-----------|-------|------|
| `controller` | `ghcr.io/zentinelproxy/zentinel-gateway` | Watches the Kubernetes API, writes `zentinel.kdl`, and updates resource status |
| `proxy` | `ghcr.io/zentinelproxy/zentinel` | Serves traffic using the generated configuration |

The two containers share two `emptyDir` volumes: one for the generated configuration (`/etc/zentinel/gateway/zentinel.kdl` by default) and one for TLS certificates taken from Secrets (`/tmp/zentinel-gateway-certs`). The proxy mounts both read-only.

On every relevant change the controller rebuilds the complete configuration from all Gateway API objects it owns, writes it atomically, and the proxy picks it up through `auto-reload`. Before the first rebuild, the controller writes a bootstrap configuration so the proxy can start: an HTTP listener on `0.0.0.0:8080` and an HTTPS listener on `0.0.0.0:8443` with a self-signed certificate.

### Listener ports

The controller does not open one proxy listener per Gateway listener. All `HTTP` listeners map to a single proxy listener on `PROXY_HTTP_PORT` (default `8080`), and all `HTTPS` listeners map to one on `PROXY_HTTPS_PORT` (default `8443`), whatever port the Gateway declares. The chart's proxy Service exposes them as ports `80` and `443`. Routes from every Gateway share these two listeners, and hostnames keep them apart.

## Supported resources

The GatewayClass must name the controller `zentinelproxy.io/gateway-controller`. Resources attached to Gateways of other classes are ignored.

| Resource | API version | Channel | Status |
|----------|-------------|---------|--------|
| `GatewayClass` | `gateway.networking.k8s.io/v1` | Standard | Supported. `parametersRef` is ignored |
| `Gateway` | `gateway.networking.k8s.io/v1` | Standard | Supported |
| `HTTPRoute` | `gateway.networking.k8s.io/v1` | Standard | Supported (see [HTTPRoute features](#httproute-features)) |
| `GRPCRoute` | `gateway.networking.k8s.io/v1` | Standard | Supported. Filters are not applied |
| `ReferenceGrant` | `gateway.networking.k8s.io/v1beta1` | Standard | Supported for cross-namespace backends and certificate Secrets |
| `TLSRoute` | `gateway.networking.k8s.io/v1alpha3` | Experimental | Accepted, but not real TLS passthrough (see [Limitations](#limitations)) |
| `TCPRoute` | `gateway.networking.k8s.io/v1alpha2` | Experimental | Status is written; no proxy configuration is generated |
| `Ingress` | `networking.k8s.io/v1` | — | Supported for class `zentinel` |
| `BackendTLSPolicy` | — | — | Not supported |
| `UDPRoute` | — | — | Not supported |

The controller also reads `Secrets` of type `kubernetes.io/tls` for listener certificates, `Services` (and `EndpointSlices` for headless Services) for backends, and `Namespaces` for `allowedRoutes` selectors.

### Gateway API version

The controller targets **Gateway API v1.4.1**, the version its conformance suite and CI run against. Install the CRDs from that release before you install the controller:

```bash
# Standard channel: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant
kubectl apply --server-side \
  -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/standard-install.yaml
```

`TLSRoute` and `TCPRoute` exist only in the experimental channel. Install it instead of the standard channel if you need them:

```bash
kubectl apply --server-side --force-conflicts \
  -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml
```

The CRD bundles are too large for client-side `kubectl apply` (the last-applied annotation exceeds its size limit), so use `--server-side`.

Gateway API v1.5 serves `TLSRoute` and `ReferenceGrant` as `v1`. The controller still watches the older versions listed above, so stay on v1.4.x CRDs.

## Installation

The Helm chart for the controller lives in the main repository at `deploy/helm/zentinel-gateway`. It is not published to a chart repository, and the separate `zentinel-helm` repository only contains the proxy chart.

{% callout(type="warning", title="Set the image tags") %}
The chart's default image tag is its `appVersion` (`0.6.1`), and no image is published under that tag. Images are tagged with the CalVer release, for example `26.10_3`. Always set `image.tag` and `proxy.image.tag`.
{% end %}

```bash
git clone --depth 1 https://github.com/zentinelproxy/zentinel.git
helm install zentinel-gateway zentinel/deploy/helm/zentinel-gateway \
  --namespace zentinel-system --create-namespace \
  --set image.tag=26.10_3 \
  --set proxy.image.tag=26.10_3
```

The chart creates:

- A `GatewayClass` named `zentinel` (`gatewayClass.create`, `gatewayClass.name`)
- A Deployment with the `controller` and `proxy` containers
- A proxy Service of type `LoadBalancer` on ports 80 and 443 (`proxy.serviceType`)
- A metrics Service on port 9090
- A ServiceAccount, ClusterRole, and ClusterRoleBinding

Both containers run as non-root (UID 65534) with a read-only root filesystem and all capabilities dropped.

{% callout(type="info", title="RBAC gaps") %}
The chart's ClusterRole does not grant access to `tcproutes` or to `discovery.k8s.io/endpointslices`. If you use `TCPRoute`, or route to headless Services (which the controller resolves through EndpointSlices), add `get`, `list`, and `watch` on those resources, plus `patch` on `tcproutes/status`.
{% end %}

### First route

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: web
  namespace: default
spec:
  gatewayClassName: zentinel
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
  namespace: default
spec:
  parentRefs:
    - name: web
  hostnames:
    - app.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: app
          port: 8080
```

```bash
kubectl get gateway web        # PROGRAMMED should be True
kubectl get httproute app -o jsonpath='{.status.parents[0].conditions}'
```

To terminate TLS, add an `HTTPS` listener with `tls.certificateRefs` pointing at a `kubernetes.io/tls` Secret. Referencing a Secret in another namespace needs a `ReferenceGrant`.

## HTTPRoute features

| Feature | Support |
|---------|---------|
| Path match `Exact`, `PathPrefix`, `RegularExpression` | Yes |
| Header match | Yes, exact value only (the match `type` is ignored) |
| Query parameter match | Yes, exact value only (the match `type` is ignored) |
| Method match | Yes |
| Hostnames, intersected with listener hostnames (including wildcards) | Yes |
| `allowedRoutes.namespaces`: `Same`, `All`, `Selector` | Yes (`Selector` evaluates `matchLabels` only) |
| `RequestHeaderModifier`, `ResponseHeaderModifier` | Yes |
| `RequestRedirect` (scheme, hostname, port, path, status code) | Yes |
| `URLRewrite` (hostname, path) | Yes |
| Weighted `backendRefs` | Yes |
| Cross-namespace `backendRefs` with `ReferenceGrant` | Yes |
| `RequestMirror`, `CORS`, `ExtensionRef` filters | No |
| Per-backendRef filters | No |
| Rule `timeouts`, `retry`, `sessionPersistence` | No |
| Backends other than core `Service` | No (reported as `InvalidKind`) |

Each backend becomes a Zentinel upstream addressed as `<service>.<namespace>.svc.cluster.local:<port>`, or as the ready pod IPs for headless Services. Every generated upstream gets an HTTP health check (`GET /`, expecting `200`, every 10 seconds). Backends that do not answer `200` on `/` are marked unhealthy, so make sure your Services serve that path.

## Ingress

The controller also handles `networking.k8s.io/v1` Ingress objects that set `spec.ingressClassName: zentinel` or the annotation `kubernetes.io/ingress.class: zentinel`. It does not create an `IngressClass` object.

- `pathType: Exact` becomes an exact match; `Prefix` and `ImplementationSpecific` become prefix matches
- `spec.defaultBackend` becomes a low-priority catch-all route
- Only numeric Service ports are supported
- `spec.tls` and controller-specific annotations are ignored, and no Ingress status is written
- Ingress routes are only generated when at least one Gateway of the `zentinel` class exists, because they are attached to that Gateway's proxy listeners

## Status reporting

| Resource | Conditions |
|----------|------------|
| GatewayClass | `Accepted` |
| Gateway | `Accepted`, `Programmed`, `status.addresses` from the proxy Service (or `GATEWAY_ADDRESS`) |
| Gateway listeners | `Accepted`, `ResolvedRefs` (`InvalidCertificateRef`, `RefNotPermitted`, `InvalidRouteKinds`), `Programmed`, `attachedRoutes` (HTTPRoutes only) |
| HTTPRoute | `Accepted` (`NoMatchingParent`, `NotAllowedByListeners`, `NoMatchingListenerHostname`), `ResolvedRefs` (`InvalidKind`, `RefNotPermitted`, `BackendNotFound`) |
| GRPCRoute, TLSRoute, TCPRoute | `Accepted` and `ResolvedRefs`, always `True` for owned parents (not validated) |

## Configuration

The controller has no command-line flags. It reads environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_OUTPUT_PATH` | unset | Where to write the generated KDL. The chart sets `<configDir>/zentinel.kdl`. Without it, no file is written |
| `PROXY_HTTP_PORT` | `8080` | Proxy bind port for all HTTP listeners |
| `PROXY_HTTPS_PORT` | `8443` | Proxy bind port for all HTTPS listeners |
| `GATEWAY_ADDRESS` | unset | IP address to report in `Gateway.status.addresses` instead of looking up the proxy Service |
| `METRICS_PORT` | `9090` | Port for the `/metrics` endpoint |
| `LEADER_ELECTION` | `false` | `true` or `1` enables Lease-based leader election |
| `POD_NAME` | generated | Identity used in the Lease |
| `RUST_LOG` | `zentinel_gateway=info,kube=warn` | Log filter; logs are JSON |

The chart's `extraEnv` value adds variables to the controller container.

### High availability

Leader election uses a `coordination.k8s.io/v1` Lease named `zentinel-gateway-controller` in the namespace `zentinel-system`. That namespace is fixed in the controller; the chart's `leaderElection.namespace` value is passed as `LEADER_ELECTION_NAMESPACE`, which the controller does not read. Install the chart into `zentinel-system` if you enable leader election.

In the current release, the leader flag only drives the `zentinel_gateway_is_leader` metric: standby replicas keep reconciling and writing status. Because each replica also carries its own proxy container, running more than one replica scales the data plane, and every replica generates the same configuration.

### Observability

The controller serves Prometheus metrics on `:9090/metrics`. It has no separate health endpoints; the chart's liveness and readiness probes use `/metrics`. Metric names start with `zentinel_gateway_`. In the current release only `zentinel_gateway_is_leader` is updated; the reconciliation and rebuild counters are registered but stay at zero.

The proxy container exposes the usual [Zentinel metrics](/reference/metrics/). The chart has a `metrics.serviceMonitor` value but no ServiceMonitor template, so create the ServiceMonitor yourself if you use the Prometheus Operator.

## Conformance

The project runs the upstream Gateway API conformance suite (v1.4.1, `GATEWAY-HTTP` profile, with the `HTTPRoute` and `ReferenceGrant` features) in CI. The most recent published report:

| Field | Value |
|-------|-------|
| Implementation version | 0.6.1 (March 2026) |
| Gateway API version / channel | v1.4.1 / standard |
| Profile | `GATEWAY-HTTP` core |
| Result | 31 passed, 2 failed (`HTTPRouteHTTPSListener`, `HTTPRouteServiceTypes`) |

No report has been published for the `GATEWAY-GRPC` or `GATEWAY-TLS` profiles, and no extended features are claimed. Reports are kept in the [`conformance/reports`](https://github.com/zentinelproxy/zentinel/tree/main/conformance/reports) directory of the main repository.

## Limitations

- **TLSRoute is not passthrough.** TLSRoutes are translated into host-matched HTTP routes; the generated configuration has no SNI passthrough, so TLS is not forwarded untouched to the backend.
- **TCPRoute has no data-plane effect.** The route is accepted in status, but no listener or upstream is generated.
- **One certificate per listener.** Additional `certificateRefs` are not written to the generated configuration; only the first certificate is served.
- **Fixed listener ports.** Gateway listener ports are mapped to the two proxy ports described [above](#listener-ports). `TLS`, `TCP`, and `UDP` listeners are rendered as plain HTTP.
- **Fixed listener and upstream settings.** Minimum TLS version 1.2, 60-second request timeout, 75-second keep-alive, and the `GET /` health check on every upstream cannot be changed from Gateway API resources.
- **No policy attachment.** There is no `parametersRef`, `BackendTLSPolicy`, or Zentinel-specific policy CRD, so agents, WAF, rate limits, and caching cannot be configured through the controller.
- **Leader election does not fence standby replicas**, and its namespace is fixed (see [High availability](#high-availability)).

If you need any of these, deploy Zentinel with a hand-written configuration as described in [Kubernetes](../kubernetes/).

## See also

- [Kubernetes](../kubernetes/): Helm chart and manifests for the proxy itself
- [Service Mesh Integration](../service-mesh/)
- [Gateway API documentation](https://gateway-api.sigs.k8s.io/)
