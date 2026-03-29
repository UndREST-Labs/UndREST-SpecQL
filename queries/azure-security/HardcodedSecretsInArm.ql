/**
 * @name Hardcoded Secrets in ARM Templates
 * @description Detects ARM template parameters typed as securestring that inadvertently include
 *              a plaintext default value. Such defaults are stored in cleartext in deployment logs
 *              and template history, defeating the purpose of the secure type.
 * @kind problem
 * @problem.severity error
 * @security-severity 9.0
 * @precision high
 * @id azure/hardcoded-secrets-arm
 * @tags security
 *       external/cwe/cwe-312
 *       external/cwe/cwe-798
 */

import javascript

from JsonObject param
where
  // Identify securestring parameters with insecure default values
  param.getPropValue("type").(JsonString).getValue() = "securestring" and
  exists(param.getPropValue("defaultValue"))
select param, "Insecure default value found on a securestring ARM parameter."
