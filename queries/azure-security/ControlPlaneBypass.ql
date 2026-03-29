/**
 * @name Control-Plane Bypass via Data-Plane Authoring
 * @description Scans data-plane specifications for resource management operations (e.g., creating
 *              deployments, accounts, or configurations) that should typically be restricted to the
 *              management plane. Such paths may enable unauthorized resource lifecycle control.
 * @kind problem
 * @problem.severity warning
 * @security-severity 7.0
 * @precision low
 * @id azure/control-plane-bypass
 * @tags security
 *       external/cwe/cwe-284
 *       external/cwe/cwe-269
 */

import javascript

from JsonString path
where
  // Scan for management nouns combined with lifecycle verbs in data-plane paths
  path.getValue().matches("%/deployments%") or
  path.getValue().matches("%/accounts%") or
  path.getValue().matches("%/configurations%")
select path, "Possible control-plane bypass: management noun found in data-plane path."
