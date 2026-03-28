/**
 * @name Azure SAS URI Exposed in API Response
 * @description Detects API specifications that emit Azure Shared Access Signature (SAS) URIs
 *              in API responses. SAS URIs contain sensitive tokens that grant time-limited
 *              access to Azure resources. Exposing these in control-plane API responses can
 *              lead to data exfiltration or unauthorized data-plane access.
 * @kind problem
 * @problem.severity error
 * @security-severity 8.5
 * @precision high
 * @id azure/sas-uri-in-response
 * @tags security
 *       external/cwe/cwe-200
 *       external/cwe/cwe-359
 */

import javascript

from JsonString sasUri
where 
  sasUri.getValue().matches("%sig=%") and
  sasUri.getValue().matches("https://%") and
  (
    sasUri.getValue().matches("%&sp=%") or
    sasUri.getValue().matches("%&se=%") or
    sasUri.getValue().matches("%&sv=%") or
    sasUri.getValue().matches("%&sr=%")
  )
select sasUri, "Found Azure SAS URI with signature token, which may lead to data exfiltration or unauthorized access"
