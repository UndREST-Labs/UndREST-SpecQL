/**
 * @name Exposed SAS Tokens and Signed URLs
 * @description Detects pre-authenticated SAS URIs or tokens found in example payloads or JSON
 *              strings. These contain sensitive signature material (sig, sv) along with scope or
 *              expiry parameters that, if exposed, can grant unauthorized access to Azure resources.
 * @kind problem
 * @problem.severity error
 * @security-severity 8.5
 * @precision high
 * @id azure/exposed-sas-tokens
 * @tags security
 *       external/cwe/cwe-200
 *       external/cwe/cwe-522
 */

import javascript

from JsonString s
where
  s.getValue().matches("%sig=%") and
  s.getValue().matches("%sv=%") and
  (
    // Matches full URLs (Logic Apps style) or token-only patterns (Storage style)
    s.getValue().matches("https://%") or
    s.getValue().matches("sv=%&%sig=%")
  ) and
  (
    // Common SAS parameters: permissions (sp), expiry (se), start (st), or resource (sr/srt)
    s.getValue().matches("%&sp=%") or
    s.getValue().matches("%&se=%") or
    s.getValue().matches("%&st=%") or
    s.getValue().matches("%&sr=%") or
    s.getValue().matches("%&srt=%")
  )
select s, "Potential SAS-style signature material detected in a spec example or JSON string."
