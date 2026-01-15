package {{PACKAGE}}.{{MODULE}}.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.resilience.annotation.CircuitBreaker;
import org.springframework.resilience.annotation.ConcurrencyLimit;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

/**
 * Service with Native Resiliency Features (Spring Boot 4).
 *
 * Spring Boot 4 includes built-in resiliency features without external libraries:
 * - @Retryable - Automatic retries on failures
 * - @CircuitBreaker - Prevent cascading failures
 * - @ConcurrencyLimit - Rate limiting and bulkhead pattern
 *
 * No need for Spring Cloud Circuit Breaker or Resilience4j!
 *
 * Benefits:
 * - Zero external dependencies
 * - Simpler configuration
 * - Lower overhead
 * - Production-ready defaults
 */
@Service
public class {{NAME}}Service {
    private static final Logger log = LoggerFactory.getLogger({{NAME}}Service.class);

    private final {{NAME}}Repository repository;
    private final External{{NAME}}Client externalClient;

    public {{NAME}}Service(
            {{NAME}}Repository repository,
            External{{NAME}}Client externalClient
    ) {
        this.repository = repository;
        this.externalClient = externalClient;
    }

    // ==================== RETRY PATTERN ====================

    /**
     * Retries failed operations automatically.
     *
     * Use cases:
     * - External API calls that may fail temporarily
     * - Database operations during brief connection issues
     * - Network operations with transient failures
     */
    @Retryable(
            maxRetries = 5L,                    // Retry up to 5 times
            delay = 2000L,                      // Wait 2s between retries
            includes = {RuntimeException.class} // Retry on these exceptions
    )
    public Optional<{{NAME}}> fetchFromExternalApi(String id) {
        log.info("Fetching {{NAME}} from external API: {}", id);
        return externalClient.getById(id);
    }

    /**
     * Retry with exponential backoff.
     */
    @Retryable(
            maxRetries = 3L,
            delay = 1000L,
            includes = {Exception.class}
    )
    public void syncWithExternalSystem(String id) {
        log.info("Syncing {{NAME}} with external system: {}", id);
        // If this fails, Spring retries with increasing delays
        externalClient.sync(id);
    }

    // ==================== CIRCUIT BREAKER PATTERN ====================

    /**
     * Circuit breaker prevents cascading failures.
     *
     * How it works:
     * - CLOSED: Normal operation, requests go through
     * - OPEN: Too many failures, requests fail fast
     * - HALF_OPEN: Testing if service recovered
     *
     * Use cases:
     * - Protect against failing downstream services
     * - Prevent resource exhaustion
     * - Fail fast when dependencies are down
     */
    @CircuitBreaker(
            failureThreshold = 5,      // Open after 5 failures
            waitDurationInOpenState = 30000L,  // Wait 30s before retry
            slidingWindowSize = 10     // Track last 10 calls
    )
    public List<{{NAME}}> fetchFromUnreliableService() {
        log.info("Calling unreliable external service");
        return externalClient.getAll();
    }

    /**
     * Circuit breaker with fallback method.
     */
    @CircuitBreaker(
            failureThreshold = 3,
            waitDurationInOpenState = 60000L,
            fallbackMethod = "getFromCache"
    )
    public {{NAME}} getWithFallback(String id) {
        return externalClient.getById(id)
                .orElseThrow(() -> new NotFoundException("{{NAME}} not found: " + id));
    }

    /**
     * Fallback method called when circuit is OPEN.
     * Must have same signature as original method.
     */
    private {{NAME}} getFromCache(String id, Throwable t) {
        log.warn("Circuit open, using cached data for: {}", id, t);
        return repository.findById(id)
                .orElseThrow(() -> new NotFoundException("{{NAME}} not in cache: " + id));
    }

    // ==================== CONCURRENCY LIMIT (BULKHEAD) ====================

    /**
     * Limits concurrent executions to prevent resource exhaustion.
     *
     * Use cases:
     * - Protect expensive operations (heavy DB queries, file processing)
     * - Prevent thread pool exhaustion
     * - Rate limiting for external API calls
     * - Implement bulkhead pattern
     */
    @ConcurrencyLimit(5)  // Max 5 concurrent executions
    public void processExpensiveOperation(String id) {
        log.info("Processing expensive operation for: {}", id);
        // Only 5 threads can execute this at the same time
        // 6th request waits until one completes
        performExpensiveWork(id);
    }

    /**
     * Rate limiting for external notifications.
     */
    @ConcurrencyLimit(2)
    public void sendNotification(String id) {
        log.info("Sending notification for: {}", id);
        // Only 2 concurrent notifications allowed
        externalClient.notify(id);
    }

    // ==================== COMBINING PATTERNS ====================

    /**
     * Combine retry + circuit breaker for robust external calls.
     *
     * Execution flow:
     * 1. Retry handles transient failures
     * 2. Circuit breaker prevents retry storms
     * 3. System fails fast when service is down
     */
    @Retryable(maxRetries = 3L, delay = 1000L, includes = {Exception.class})
    @CircuitBreaker(failureThreshold = 5, waitDurationInOpenState = 30000L)
    public {{NAME}} fetchWithResiliency(String id) {
        return externalClient.getById(id)
                .orElseThrow(() -> new NotFoundException("{{NAME}} not found: " + id));
    }

    /**
     * Combine concurrency limit + retry for controlled external calls.
     */
    @ConcurrencyLimit(3)
    @Retryable(maxRetries = 2L, delay = 500L)
    public void syncWithRateLimit(String id) {
        externalClient.sync(id);
    }

    // ==================== HELPER METHODS ====================

    private void performExpensiveWork(String id) {
        // Simulate expensive operation
        try {
            Thread.sleep(3000);
            log.info("Completed expensive work for: {}", id);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public List<{{NAME}}> findAll() {
        return repository.findAll();
    }

    public Optional<{{NAME}}> findById(String id) {
        return repository.findById(id);
    }
}

// ============================================================
// CONFIGURATION (application.yml)
// ============================================================

// spring:
//   resilience:
//     retry:
//       enabled: true
//       max-attempts: 3
//       wait-duration: 1s
//     circuit-breaker:
//       enabled: true
//       failure-rate-threshold: 50
//       wait-duration-in-open-state: 30s
//     rate-limiter:
//       enabled: true
//       limit-for-period: 10
//       limit-refresh-period: 1s

// ============================================================
// MONITORING AND OBSERVABILITY
// ============================================================

// Add Spring Boot Actuator to monitor resilience metrics:
//
// management:
//   endpoints:
//     web:
//       exposure:
//         include: health,metrics,resilience
//   metrics:
//     enable:
//       resilience: true
//
// Metrics available at: /actuator/metrics
// - resilience.retry.calls
// - resilience.circuitbreaker.state
// - resilience.bulkhead.concurrent.calls

// ============================================================
// TESTING RESILIENCE
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.service;
//
// import org.junit.jupiter.api.Test;
// import org.springframework.beans.factory.annotation.Autowired;
// import org.springframework.boot.test.context.SpringBootTest;
// import org.springframework.boot.test.mock.mockito.MockBean;
//
// import static org.assertj.core.api.Assertions.assertThat;
// import static org.mockito.Mockito.*;
//
// @SpringBootTest
// class {{NAME}}ServiceTest {
//
//     @Autowired
//     {{NAME}}Service service;
//
//     @MockBean
//     External{{NAME}}Client externalClient;
//
//     @Test
//     void shouldRetryOnFailure() {
//         when(externalClient.getById(anyString()))
//                 .thenThrow(new RuntimeException("Transient failure"))
//                 .thenThrow(new RuntimeException("Transient failure"))
//                 .thenReturn(Optional.of(new {{NAME}}()));
//
//         var result = service.fetchFromExternalApi("123");
//
//         assertThat(result).isPresent();
//         verify(externalClient, times(3)).getById("123");
//     }
//
//     @Test
//     void shouldOpenCircuitAfterFailures() {
//         when(externalClient.getAll())
//                 .thenThrow(new RuntimeException("Service down"));
//
//         // First 5 calls should try and fail
//         for (int i = 0; i < 5; i++) {
//             try {
//                 service.fetchFromUnreliableService();
//             } catch (Exception ignored) {}
//         }
//
//         // Circuit should be open now, failing fast
//         // (Test framework needed to verify circuit state)
//     }
// }

// ============================================================
// BEST PRACTICES
// ============================================================

// 1. Don't overuse @Retryable - only for truly transient failures
// 2. Set reasonable retry delays to avoid overwhelming downstream
// 3. Use circuit breakers for external service calls
// 4. Monitor circuit breaker states in production
// 5. Implement fallback methods for critical operations
// 6. Use concurrency limits for resource-intensive operations
// 7. Test resilience behavior with fault injection
// 8. Configure appropriate thresholds based on SLAs
