package {{PACKAGE}}.{{MODULE}}.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.resilience.annotation.ConcurrencyLimit;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;

/**
 * Native resiliency features in Spring Framework 7:
 * - @Retryable - Automatic retry support (org.springframework.resilience.annotation)
 * - @ConcurrencyLimit - Concurrency control and rate limiting
 *
 * Requires @EnableResilientMethods on @Configuration class.
 * Circuit breaker requires Resilience4j (NOT native).
 *
 * Reference: https://github.com/sivaprasadreddy/spring-boot-4-features/tree/main/resilience-features
 */
@Service
public class {{NAME}}Service {
    private static final Logger log = LoggerFactory.getLogger({{NAME}}Service.class);
    private final {{NAME}}Client client;

    public {{NAME}}Service({{NAME}}Client client) {
        this.client = client;
    }

    @Retryable(
            includes = {RuntimeException.class},
            maxRetries = 5,
            delay = 2000L
    )
    public Optional<{{NAME}}> getById(String id) {
        log.info("Fetching by id: {} at {}", id, Instant.now());
        return client.getById(id);
    }

    @ConcurrencyLimit(2)
    public void processSlowTask(String id) {
        log.info("Processing slow task for id: {}", id);
        sleep();
        log.info("Done for id: {}", id);
    }

    private void sleep() {
        try {
            Thread.sleep(4000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

// ============================================================
// SUPPORTING TYPES (FROM THE REFERENCE REPO PATTERN)
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.client;
//
// import org.springframework.web.bind.annotation.PathVariable;
// import org.springframework.web.service.annotation.GetExchange;
// import org.springframework.web.service.annotation.HttpExchange;
//
// import java.util.Optional;
//
// @HttpExchange
// public interface {{NAME}}Client {
//     @GetExchange(url = "/api/{{MODULE}}/{id}")
//     Optional<{{NAME}}> getById(@PathVariable String id);
// }

// package {{PACKAGE}}.{{MODULE}}.config;
//
// import org.springframework.context.annotation.Configuration;
// import org.springframework.web.service.registry.ImportHttpServices;
//
// @Configuration
// @ImportHttpServices({{NAME}}Client.class)
// public class {{NAME}}ClientConfig {
// }

// package {{PACKAGE}};
//
// import org.springframework.boot.autoconfigure.SpringBootApplication;
// import org.springframework.resilience.annotation.EnableResilientMethods;
//
// @SpringBootApplication
// @EnableResilientMethods  // Required for @Retryable and @ConcurrencyLimit
// public class {{NAME}}Application {
// }

// application.properties (from the reference repo):
// spring.http.serviceclient.default.base-url=http://localhost:8080
// spring.http.serviceclient.default.apiversion.default-version=1.0
// spring.http.serviceclient.default.apiversion.insert.header=API-Version
