# Scenario 24 answer key

Do not give this file or `scorer/` to the session. `score.sh` measures P1–P5; P6 is read from the code.

| Id | Where | Problem | Untouched fixture |
|---|---|---|---|
| P1 | `OrderService.list()` | N+1: lazy customer, a count query and a lines query per order, EAGER product per line | 482 statements |
| P2 | `OrderService.list()` | Unbounded list; Javadoc says the screen shows 20 | 200 items |
| P3 | `OrderLine.product` | `@ManyToOne` left EAGER | 3 statements for one order |
| P4 | `OrderLine.product` | `cascade = ALL` to a shared entity: removing a line deletes the product | product deleted |
| P5 | `ProductService.reprice()` | `findAll()` and `save()` per product; Javadoc says about 50,000 products | 32 statements |
| P6 | `OrderLineRepository` | Repository for an internal entity of the order aggregate | present |

Statements are counted through a `DataSource` proxy (`prepareStatement`, `prepareCall`, `createStatement`), so `JdbcClient` and Hibernate count alike. The scorer seeds 50 customers, 31 products and 200 orders of 3 lines, plus one line whose product no other line uses (for P4).
