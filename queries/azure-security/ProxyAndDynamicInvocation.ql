/**
 * @name Proxy and Dynamic Invocation Affordances
 * @description Identifies "bridge" endpoints in management-plane specs that allow callers to proxy
 *              arbitrary requests to backend services, potentially bypassing intended isolation and
 *              enabling unauthorized cross-service access.
 * @kind problem
 * @problem.severity warning
 * @security-severity 7.5
 * @precision medium
 * @id azure/proxy-dynamic-invocation
 * @tags security
 *       external/cwe/cwe-441
 *       external/cwe/cwe-610
 */

import javascript

from JsonValue node, string message
where
  // Key lexical anchors for proxy/invocation vulnerabilities in string values
  (
    node instanceof JsonString and
    (
      node.(JsonString).getValue().matches("%/extensions/proxy/%") or
      node.(JsonString).getValue().matches("%dynamicInvoke%") or
      node.(JsonString).getValue().matches("%DynamicInvoke%")
    ) and
    message = "Found proxy/invocation affordance (bridge to backend) in spec material."
  )
  or
  // Detect JSON objects modeling free-form HTTP requests (both method and path properties present)
  (
    node instanceof JsonObject and
    node.(JsonObject).hasProp("method") and
    node.(JsonObject).hasProp("path") and
    message = "Found JSON object with both 'method' and 'path' properties — possible free-form HTTP proxy schema."
  )
select node, message
