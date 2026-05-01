+++
title = "Multi-tenant TLS"
weight = 12
updated = 2026-05-01
+++

A complete configuration for serving multiple tenants on a single HTTPS listener, where each tenant has its own ACME-managed certificate with an independent renewal lifecycle. This example uses [per-SNI ACME](@/configuration/listeners.md#per-sni-acme), available since `26.05_1`.

## Use case

You operate a SaaS platform that serves customer-owned domains (`customer-a.com`, `customer-b.com`, etc.) alongside your own (`example.com`). You need:

- Each tenant's certificate issued and renewed automatically.
- A failure renewing one tenant (e.g. DNS-01 stuck waiting for propagation) **must not** delay any other tenant's renewal.
- Independent ACME accounts per tenant — different contact emails, different storage paths so cert state stays isolated, optionally different challenge providers.
- The platform's primary domain on the same listener as a "root" ACME-managed certificate.

## Architecture

```
                                       ┌─ Tenant A scheduler (HTTP-01) ─→ tenant-a.com
                                       │
  Client ──TLS─▶ Zentinel listener ────┼─ Tenant B scheduler (DNS-01)  ─→ *.tenant-b.com
                                       │
                                       ├─ Manual cert ─────────────────→ partner-domain.com
                                       │
                                       └─ Root ACME scheduler ─────────→ example.com
```

Each ACME block instantiates its own `RenewalScheduler` and `AcmeClient` ("Option B" architecture). They run as independent background tasks so a stuck issuance is contained to that tenant's lifecycle.

## Configuration

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"

    tls {
        // Root ACME: covers the platform's primary domain.
        acme {
            email "ops@example.com"
            domains "example.com" "www.example.com"
        }

        additional-certs {
            // Tenant A: HTTP-01, default storage layout.
            sni-cert {
                acme {
                    email "tenant-a@example.com"
                    domains "customer-a.com" "www.customer-a.com"
                }
            }

            // Tenant B: DNS-01 wildcard via Cloudflare,
            // separate storage path, separate ACME account.
            sni-cert {
                acme {
                    email "tenant-b@example.com"
                    domains "*.customer-b.com" "customer-b.com"
                    challenge-type "dns-01"
                    storage "/var/lib/zentinel/acme/tenant-b"
                    dns-provider {
                        cloudflare {
                            api-token-file "/etc/zentinel/secrets/tenant-b-cf-token"
                        }
                    }
                }
            }

            // A partner who supplied their own certificate — manual
            // and ACME-managed sni-certs coexist on the same listener.
            sni-cert {
                hostnames "partner-domain.com"
                cert-file "/etc/zentinel/certs/partner.crt"
                key-file "/etc/zentinel/certs/partner.key"
            }
        }
    }
}
```

## Notes

### Implicit hostnames

The Tenant A and Tenant B blocks omit `hostnames` and rely on the [implicit derivation](@/configuration/listeners.md#per-sni-acme): routing hostnames come from each block's `acme.domains` list. The wildcard pattern is preserved (`*.customer-b.com` becomes a wildcard SNI route, exact `customer-b.com` becomes an exact match).

### Storage path isolation

Tenant B uses an explicit `storage` directory. Tenant A and the root ACME share the default storage. Zentinel enforces [global domain uniqueness](@/configuration/listeners.md#per-sni-acme) at config-validation time, so even if two blocks accidentally claimed the same domain, the validator rejects the config before any storage collision can occur.

### First-start behavior

On the very first run, none of the ACME-managed certificates exist on disk. Zentinel logs a structured warning per missing cert (with `listener_id`, `sni_index`, and `primary_domain`) and increments `zentinel_tls_sni_cert_skip_total`. Issuance starts in the background; once a challenge completes, that cert is hot-reloaded into the SNI resolver without restart.

If a cert is still missing after issuance should have completed (typical: minutes for HTTP-01, up to an hour for DNS-01 propagation), check the metric and the structured warning — they identify the listener and SNI slot that is stuck.

## Operational checklist

- [ ] Each tenant's `email` is reachable for ACME account recovery and CA notifications.
- [ ] Each `storage` path is on persistent disk (not ephemeral container storage), and backed up.
- [ ] DNS-01 credentials are scoped per tenant — the Cloudflare API token in the example is restricted to Tenant B's zone only.
- [ ] HTTP-01 challenges require the listener to also be reachable on port 80 (Zentinel's challenge manager binds there). Add a port-80 listener if you have not already.
- [ ] Monitor `zentinel_tls_sni_cert_skip_total` — a non-zero value an hour after startup means an issuance is failing and the corresponding tenant is being served the listener default certificate (which will produce a CN/SAN-mismatch warning in clients).
