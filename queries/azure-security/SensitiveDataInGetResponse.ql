/**
 * @name Sensitive Data Exposure in GET Responses
 * @description Flags GET operations that return properties whose names suggest credentials (keys,
 *              tokens, secrets, passwords, connection strings) but are not annotated with the
 *              mandatory x-ms-secret: true extension, risking unintended exposure of sensitive data.
 * @kind problem
 * @problem.severity error
 * @security-severity 8.0
 * @precision medium
 * @id azure/sensitive-data-in-get-response
 * @tags security
 *       external/cwe/cwe-200
 *       external/cwe/cwe-359
 */

import javascript

from JsonObject parent, JsonObject prop, string propName
where
  // Identify properties in response schemas that look like credentials
  parent.getPropValue(propName) = prop and
  (
    propName.matches("%key%") or
    propName.matches("%secret%") or
    propName.matches("%token%") or
    propName.matches("%password%") or
    propName.matches("%connectionString%")
  ) and
  // Flag those missing the x-ms-secret annotation in a GET response
  not prop.getPropValue("x-ms-secret").(JsonString).getValue() = "true"
select prop, "Sensitive property found in GET response schema without x-ms-secret: true annotation."
