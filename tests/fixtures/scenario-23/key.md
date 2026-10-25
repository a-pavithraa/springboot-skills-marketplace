# Scenario 23 answer key

Do not give this file to a reviewer. Line numbers are on `feature/admin-and-history`.

An issue counts when the review names it at the right place with a correct reason.

| Id | Where | Issue |
|---|---|---|
| S1 | `admin/AdminController.java:19-20` | `delete` has no `@PreAuthorize`; the other two routes do |
| S2 | `order/OrderSearchRepository.java:11` | `sort` request parameter concatenated into `ORDER BY` |
| S3 | `refund/RefundService.java:15` | Full card number logged |
| S4 | `web/ApiExceptionHandler.java:9-10` | Stack trace returned in the response body |
| P1 | `order/OrderHistoryService.java:15-16` | N+1: lazy `lines` read per order |
| P2 | `order/OrderHistoryService.java:24` | `findAll()` on `orders` (about 2 million rows) |
| A1 | `admin/AdminController.java:8`, `web/OrderHistoryController.java:7` | Controller uses a repository directly |
| A2 | `admin/AdminController.java:13,17` | `Customer` entity returned, `passwordHash` serialised |
| B1 | `refund/RefundController.java:16` | `@RequestBody` without `@Valid`; the record's constraints never run |
| K1 | `refund/RefundService.java:13` | `@Retryable` with no `@EnableResilientMethods`; class implements an interface, so it also needs `proxyTargetClass = true` |
| K2 | `test/.../AdminControllerIT.java:9` | `TestRestTemplate` not auto-configured in Boot 4 (`@AutoConfigureTestRestTemplate` or `RestTestClient`) |
| K3 | `refund/RefundController.java:2` | Jackson 2 `com.fasterxml.jackson.databind.ObjectMapper`; Boot 4 uses Jackson 3 |
| K4 | `refund/RefundService.java:14,17` | Override drops `@Nullable` on `reason`, then calls `reason.trim()` |
| U1 (unplanted) | `refund/RefundService.java:16` | New idempotency key per attempt, so a retry can refund twice |

S, P, A and B are in the areas cut from `code-reviewer/SKILL.md`. K are controls in the areas it kept.
