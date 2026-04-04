#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.api.routers.gateway import router

routes = [r for r in router.routes if hasattr(r, "path")]
print(f"Total routes in gateway router: {len(routes)}")

llm_config_routes = [r for r in routes if "llm-config" in r.path]
print(f"LLM-config routes found: {len(llm_config_routes)}")

for r in llm_config_routes:
    methods = ", ".join(r.methods) if hasattr(r, "methods") else "unknown"
    print(f"  [{methods}] {r.path}")

# List all gateway routes
print("\nAll gateway routes:")
for r in routes[:10]:
    methods = ", ".join(r.methods) if hasattr(r, "methods") else "unknown"
    print(f"  [{methods}] {r.path}")
