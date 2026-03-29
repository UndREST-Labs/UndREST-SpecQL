/**
 * @name Base64-Encoded Secret Detection
 * @description Searches for high-entropy strings or fields explicitly formatted as base64-encoded
 *              bytes that may mask obfuscated secrets within API examples or schema definitions.
 * @kind problem
 * @problem.severity warning
 * @security-severity 6.5
 * @precision low
 * @id azure/base64-encoded-secret
 * @tags security
 *       external/cwe/cwe-312
 *       external/cwe/cwe-522
 */

import javascript

from JsonValue node, string message
where
  // Detects base64-encoded strings of significant length (likely secrets).
  // Uses regexpMatch for character-class matching since matches() uses SQL-style wildcards.
  (
    node instanceof JsonString and
    node.(JsonString).getValue().regexpMatch("[A-Za-z0-9+/=]{20,}") and
    message = "Potential base64-encoded secret detected in spec example or schema."
  )
  or
  // Flag schema properties explicitly defined as base64-encoded bytes
  (
    node instanceof JsonObject and
    node.(JsonObject).getPropValue("format").getValue() = "byte" and
    message = "Schema property uses byte (base64) format — verify it does not expose a secret."
  )
select node, message
