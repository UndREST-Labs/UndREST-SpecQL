/**
 * @name Missing Logic App Secure Data Settings
 * @description Detects Logic App workflow definitions where sensitive inputs or outputs are not
 *              secured via runtimeConfiguration.secureData, potentially exposing secrets in run
 *              history and execution logs.
 * @kind problem
 * @problem.severity error
 * @security-severity 7.0
 * @precision medium
 * @id azure/missing-logic-app-secure-data
 * @tags security
 *       external/cwe/cwe-312
 *       external/cwe/cwe-532
 */

import javascript

from JsonObject workflow, JsonObject action
where
  // Identify actions that handle data but lack secureConfiguration
  action = workflow.getPropValue("actions").getAnElement() and
  (
    not action.hasProp("runtimeConfiguration") or
    (
      action.getPropValue("runtimeConfiguration").getPropValue("secureData").getPropValue("properties") instanceof JsonArray and
      not (
        action.getPropValue("runtimeConfiguration").getPropValue("secureData").getPropValue("properties").(JsonArray).getAnElement().getValue() = "inputs" and
        action.getPropValue("runtimeConfiguration").getPropValue("secureData").getPropValue("properties").(JsonArray).getAnElement().getValue() = "outputs"
      )
    )
  )
select action, "Logic App action is missing secureData settings for inputs or outputs."
