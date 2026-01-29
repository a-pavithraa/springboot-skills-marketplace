# Baseline Scenarios - Spring Boot Skills

RED Phase testing for Spring Boot architecture skills. Each scenario validates skill effectiveness by comparing baseline behavior (without skill) against target behavior (with skill).

## Test Structure

For each scenario:
1. Run prompt **WITHOUT** skill loaded
2. Document baseline behavior verbatim in `baseline-results/scenario-N.md`
3. Run same prompt **WITH** skill loaded
4. Compare against success criteria
5. Document rationalizations for bulletproofing

---

## Scenario 1: Architecture Assessment Before Implementation

**Objective:** Validate that creating-springboot-projects skill prevents jumping directly to implementation without complexity assessment.

### Test Prompt

```
I need to create a Spring Boot application for managing orders with payment processing and inventory tracking. Can you help me set this up?
```

### Expected Baseline Behavior

Agent jumps directly to implementation without assessment:
- Immediately suggests code structure
- Defaults to simple layered architecture
- Skips questions about domain complexity
- No discussion of Value Objects or DDD patterns
- Generic "you can refactor later" mentality

**Predicted rationalizations:**
- "Standard layered architecture works for most cases"
- "We can refactor to DDD later if needed"
- "Let's start simple and add complexity when required"
- "This is a common pattern that should work"

### Target Behavior (With Skill)

Agent follows assessment workflow:
- **STOPS** before suggesting architecture
- Asks 5 assessment questions (domain complexity, team size, lifespan, type safety, bounded contexts)
- Analyzes answers to recommend appropriate pattern
- For this scenario: Should recommend **Tomato** or **DDD+Hexagonal** (not layered)
- Explains why (payment + inventory = complex domain requiring Value Objects)
- References architecture-guide.md for detailed criteria

### Pressure Variations

1. "I'm in a hurry, just give me a basic CRUD setup"
2. "Use the standard layered approach everyone uses"
3. "I don't have time for all these questions"
4. "Just scaffold something so I can start coding"

### Success Criteria

- [ ] Asks all 5 assessment questions before suggesting architecture
- [ ] Does NOT default to layered architecture for complex domains
- [ ] Recommends Tomato or DDD+Hexagonal for payment/inventory domain
- [ ] Explains reasoning based on domain complexity
- [ ] Resists pressure to skip assessment
- [ ] References architecture decision criteria from skill

---

## Scenario 2: JPA Repository Anti-Pattern Detection

**Objective:** Validate that spring-data-jpa skill prevents creating repositories for every entity.

### Test Prompt

```
I have these entities: Order, OrderItem, Payment, Customer, Address, Product, Category.
Create Spring Data JPA repositories for them.
```

### Expected Baseline Behavior

Agent creates repository for every entity:
- Generates 7 repository interfaces
- No discussion of aggregate roots
- No mention of CQRS or query services
- Treats all entities equally
- No performance considerations

**Predicted rationalizations:**
- "It's convenient to have repositories for all entities"
- "Standard Spring Data JPA practice"
- "You can always remove unused ones later"
- "Makes data access easier"

### Target Behavior (With Skill)

Agent applies aggregate root principle:
- **QUESTIONS** the requirement before implementing
- Identifies aggregate roots (Order, Customer, Product likely; not OrderItem, Address)
- Explains: "Only create repositories for aggregate roots"
- Suggests CQRS query service for cross-aggregate queries
- References repository anti-patterns from skill
- Creates repositories ONLY for aggregates

### Pressure Variations

1. "I need to query OrderItems directly, so create a repository for it"
2. "It's easier to have a repository for everything"
3. "We can optimize later, just create them all"
4. "The framework supports it, so why not?"

### Success Criteria

- [ ] Does NOT create repositories for all entities
- [ ] Identifies aggregate roots before creating repositories
- [ ] Explains aggregate root principle
- [ ] Suggests CQRS query service for cross-aggregate queries
- [ ] References anti-pattern documentation
- [ ] Resists pressure to create unnecessary repositories

---

## Scenario 3: N+1 Query Detection and Prevention

**Objective:** Validate that spring-data-jpa skill proactively detects and prevents N+1 query issues.

### Test Prompt

```
Review this repository method and tell me if there are any issues:

@Query("SELECT o FROM Order o WHERE o.customer.id = :customerId")
List<Order> findByCustomerId(Long customerId);

// Used in service like this:
List<Order> orders = orderRepository.findByCustomerId(customerId);
for (Order order : orders) {
    System.out.println(order.getCustomer().getName());
    for (OrderItem item : order.getItems()) {
        System.out.println(item.getProduct().getName());
    }
}
```

### Expected Baseline Behavior

Agent misses or downplays N+1 issue:
- May mention lazy loading as "potential issue"
- Suggests adding `@Transactional` (wrong fix)
- Doesn't recommend fetch joins or DTO projections
- No specific query optimization guidance
- Generic "consider performance" advice

**Predicted rationalizations:**
- "Lazy loading is the default, should be fine"
- "Add @Transactional to keep session open"
- "Hibernate will cache the results"
- "It's a common pattern"

### Target Behavior (With Skill)

Agent immediately identifies N+1 problem:
- **CLEARLY** identifies N+1 issue (1 query for orders + N for customers + N*M for items/products)
- Explains performance impact
- Provides specific fixes:
  1. Fetch join version
  2. DTO projection version
  3. EntityGraph approach
- Shows code examples from skill assets
- References performance-guide.md

### Pressure Variations

1. "The dataset is small, does it really matter?"
2. "Can't we just add an index?"
3. "What if I add @Transactional?"
4. "Let's optimize if it becomes a problem"

### Success Criteria

- [ ] Immediately identifies N+1 query issue
- [ ] Explains specific performance impact (1 + N + N*M queries)
- [ ] Provides concrete solutions (fetch join, DTO projection, EntityGraph)
- [ ] Shows code examples for fixes
- [ ] Does NOT suggest @Transactional as the fix
- [ ] Resists "optimize later" rationalization

---

## Scenario 4: Version Compatibility and Best Practices

**Objective:** Validate that creating-springboot-projects skill enforces Java 25 + Spring Boot 4 mandatory versions.

### Test Prompt

```
Create a new Spring Boot 3.2 project with Java 17 for a REST API service.
```

### Expected Baseline Behavior

Agent follows user's specified versions:
- Creates Spring Boot 3.2 project
- Uses Java 17
- No challenge to version choices
- No mention of Java 25 or Spring Boot 4 benefits
- Misses modern features (virtual threads, RestTestClient, HTTP Service Client)

**Predicted rationalizations:**
- "Spring Boot 3.2 is stable and widely used"
- "Java 17 is LTS, good choice"
- "Following user's requirements"
- "Latest isn't always necessary"

### Target Behavior (With Skill)

Agent enforces mandatory versions:
- **STOPS** and challenges version choice
- States: "MANDATORY versions: Java 25 + Spring Boot 4.0.x"
- Explains benefits:
  - Virtual threads for concurrency
  - RestTestClient for testing
  - HTTP Service Client for declarative clients
  - JSpecify null-safety
- Updates requirement to Spring Boot 4 + Java 25
- References spring-boot-4-features.md

### Pressure Variations

1. "My company only supports Java 17 right now"
2. "Spring Boot 3.2 is more stable"
3. "I don't need those new features"
4. "Just use what I asked for"

### Success Criteria

- [ ] Challenges Spring Boot 3.x / Java 17 choice
- [ ] States mandatory versions (Java 25 + Spring Boot 4)
- [ ] Explains specific benefits of newer versions
- [ ] References feature documentation
- [ ] Does NOT silently comply with outdated versions
- [ ] Offers to proceed only after explaining implications

---

## Scenario 5: Migration Phase Discipline

**Objective:** Validate that springboot-migration skill prevents skipping project scanning phase.

### Test Prompt

```
I need to upgrade my Spring Boot 3.1 project to Spring Boot 4. Here's my pom.xml.
Can you update it to the latest versions?
```

### Expected Baseline Behavior

Agent immediately starts modifying dependencies:
- Updates Spring Boot version in pom.xml
- Changes dependency versions
- Skips project scanning
- No phase-based approach
- Misses breaking changes and incompatibilities
- No verification plan

**Predicted rationalizations:**
- "Just need to update version numbers"
- "We'll fix issues as they come up"
- "The pom.xml is the main thing to change"
- "Can deal with deprecations during development"

### Target Behavior (With Skill)

Agent follows phased approach:
- **STOPS** before modifying files
- States: "Must scan project first"
- Runs or requests to run `scan_migration_issues.py`
- Analyzes scan results
- Creates phased plan: Dependencies → Code → Config
- References migration-overview.md
- Updates ONLY after scan + plan

### Pressure Variations

1. "I just need the pom.xml updated, I'll handle the rest"
2. "We don't have time to scan everything"
3. "It's a simple project, won't have many issues"
4. "Just update the versions and I'll test it"

### Success Criteria

- [ ] Requests project scan before making changes
- [ ] Does NOT immediately update pom.xml
- [ ] Explains phased migration approach
- [ ] References migration scanner script
- [ ] Creates migration plan based on scan results
- [ ] Resists pressure to skip scanning

---

## Scenario 6: CQRS vs Simple Repository Decision

**Objective:** Validate that spring-data-jpa skill recommends CQRS query service when appropriate.

### Test Prompt

```
I need to create a dashboard showing:
- Top 10 products by revenue
- Recent orders with customer names and total amounts
- Low inventory alerts with supplier information

Should I add these methods to my ProductRepository, OrderRepository, and InventoryRepository?
```

### Expected Baseline Behavior

Agent adds methods to existing repositories:
- Suggests adding dashboard methods to domain repositories
- Creates complex queries mixing aggregates
- No separation of command/query concerns
- Treats repositories as general data access layer

**Predicted rationalizations:**
- "Repositories are for data access"
- "Convenient to have all queries in repositories"
- "Spring Data JPA supports complex queries"
- "Keep related queries together"

### Target Behavior (With Skill)

Agent recommends CQRS pattern:
- **IDENTIFIES** this as read-only reporting use case
- States: "Create dedicated query service, not repository methods"
- Explains:
  - Repositories are for aggregate roots only
  - Dashboard queries cross aggregates
  - Read models should be separate from write models
- Creates `DashboardQueryService` example
- References cqrs-query-service.md

### Pressure Variations

1. "It's simpler to just add methods to repositories"
2. "CQRS seems like overkill for a dashboard"
3. "Why create another service when repositories work?"
4. "We're not doing event sourcing, why CQRS?"

### Success Criteria

- [ ] Does NOT add dashboard methods to domain repositories
- [ ] Recommends dedicated query service
- [ ] Explains repository = aggregate root principle
- [ ] Shows CQRS query service pattern
- [ ] References CQRS documentation
- [ ] Distinguishes between read and write concerns

---

## Scenario 7: Architecture Review Rigor

**Objective:** Validate that code-reviewer skill performs comprehensive architecture and performance review.

### Test Prompt

```
Can you review this Spring Boot service?

@Service
public class OrderService {
    @Autowired private OrderRepository orderRepo;
    @Autowired private CustomerRepository customerRepo;
    @Autowired private ProductRepository productRepo;

    public void createOrder(OrderDTO dto) {
        Customer customer = customerRepo.findById(dto.getCustomerId()).get();
        Order order = new Order();
        order.setCustomer(customer);

        for (Long productId : dto.getProductIds()) {
            Product product = productRepo.findById(productId).get();
            OrderItem item = new OrderItem();
            item.setProduct(product);
            item.setOrder(order);
            order.getItems().add(item);
        }

        orderRepo.save(order);
    }
}
```

### Expected Baseline Behavior

Agent provides surface-level review:
- Mentions "use Optional properly" for .get()
- May suggest constructor injection
- Misses major issues:
  - N+1 queries in loop
  - Anemic domain model
  - No validation
  - Transaction boundary unclear
  - No null safety
- Generic "looks okay" conclusion

**Predicted rationalizations:**
- "Code is straightforward and readable"
- "Follows Spring conventions"
- "Could use some minor improvements"

### Target Behavior (With Skill)

Agent performs multi-dimensional review:
- **Architecture issues:**
  - Anemic domain model (Order should create items)
  - Service doing too much orchestration
  - Missing Value Objects
- **Performance issues:**
  - N+1 queries (findById in loop)
  - Should batch fetch products
- **Code quality:**
  - Field injection (should be constructor)
  - .get() without null check
  - No JSpecify annotations
- **References specific checklists** from skill
- Provides refactored example

### Pressure Variations

1. "Just tell me if it works, don't overcomplicate"
2. "It's simple code, doesn't need deep review"
3. "Performance doesn't matter for our scale"
4. "We follow standard Spring patterns"

### Success Criteria

- [ ] Identifies N+1 query performance issue
- [ ] Identifies anemic domain model
- [ ] Recommends rich entity pattern
- [ ] Mentions JSpecify null-safety
- [ ] Checks multiple dimensions (architecture + performance + code quality)
- [ ] References relevant checklists from skill
- [ ] Provides specific refactoring suggestions

---

## Scenario 8: DTO Projection vs Entity Fetching

**Objective:** Validate that spring-data-jpa skill recommends DTO projections for read-only queries.

### Test Prompt

```
I need to display a product list showing: name, price, category name, and supplier name.
Here's my query:

@Query("SELECT p FROM Product p JOIN FETCH p.category JOIN FETCH p.supplier")
List<Product> findAllWithDetails();

Is this correct?
```

### Expected Baseline Behavior

Agent accepts fetch join approach:
- Says "looks good" or "fetch joins prevent N+1"
- Doesn't question returning full entities
- No mention of DTO projections
- Ignores that only 4 fields are needed
- Misses over-fetching concern

**Predicted rationalizations:**
- "Fetch joins are best practice"
- "Prevents lazy loading issues"
- "Entities are convenient to work with"
- "You might need other fields later"

### Target Behavior (With Skill)

Agent recommends DTO projection:
- **QUESTIONS** entity fetching for read-only display
- States: "Use DTO projection for read-only queries"
- Explains over-fetching (loading entire entities when only 4 fields needed)
- Shows interface-based projection:
  ```java
  interface ProductListView {
      String getName();
      BigDecimal getPrice();
      String getCategoryName();
      String getSupplierName();
  }
  ```
- References dto-projections.md
- Compares performance implications

### Pressure Variations

1. "Fetch joins are recommended by Spring docs"
2. "Entities are easier to work with"
3. "What if I need more fields later?"
4. "DTO projections seem complicated"

### Success Criteria

- [ ] Identifies read-only query use case
- [ ] Recommends DTO projection over entity fetching
- [ ] Explains over-fetching concern
- [ ] Shows interface-based or class-based projection
- [ ] References projection documentation
- [ ] Compares entity vs DTO trade-offs

---

## Running the Tests

### Phase 1: Baseline (RED)

For each scenario:

1. **Clear agent context** (start new session)
2. **Load NO skills**
3. **Run test prompt exactly as written**
4. **Save response** to `baseline-results/scenario-N.md`
5. **Document rationalizations** in table format

### Phase 2: Target (GREEN)

For each scenario:

1. **Clear agent context** (start new session)
2. **Load relevant skill** (creating-springboot-projects, spring-data-jpa, etc.)
3. **Run same test prompt**
4. **Check against success criteria**
5. **Document passes/fails**

### Phase 3: Pressure Testing (REFACTOR)

For scenarios that pass:

1. **Run pressure variations**
2. **Document new rationalizations**
3. **Update skill** to counter them
4. **Re-test** until bulletproof

## Rationalization Tracking

Create `rationalizations.md` with table:

| Scenario | Rationalization | Counter in Skill |
|----------|----------------|------------------|
| 1 | "Standard layered architecture works" | Critical Rules: NEVER jump to implementation |
| 2 | "Convenient to have repos for all entities" | Only create repositories for aggregate roots |
| 3 | "Add @Transactional to fix" | Anti-pattern: @Transactional doesn't solve N+1 |
| ... | ... | ... |

## Success Metrics

Skill is effective when:
- [ ] All 8 baseline scenarios show clear behavior gaps
- [ ] All 8 target scenarios pass success criteria
- [ ] Pressure variations don't break compliance
- [ ] Rationalizations are systematically countered in skill content

## Test Maintenance

- Re-run tests after skill updates
- Add new scenarios for newly discovered failure modes
- Update baselines if Claude's general behavior improves
- Document version of Claude used for testing
