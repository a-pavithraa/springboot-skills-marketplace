package {{PACKAGE}}.{{MODULE}}.rest;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.springframework.web.client.ApiVersionInserter;
import org.springframework.web.context.WebApplicationContext;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;

/**
 * Integration test using TestRestClient (Spring Boot 4 modern testing API).
 *
 * TestRestClient replaces TestRestTemplate with:
 * - Fluent, readable API
 * - Better type safety with ParameterizedTypeReference
 * - Built-in API versioning support
 * - Integrated with WebTestClient patterns
 * - More intuitive assertions
 *
 * Combined with Testcontainers for realistic integration testing.
 */
@SpringBootTest(webEnvironment = RANDOM_PORT)
@Testcontainers
class {{NAME}}ControllerIntegrationTest {

    @Autowired
    private WebApplicationContext context;

    private RestTestClient client;

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres =
            new PostgreSQLContainer<>(DockerImageName.parse("postgres:18-alpine"));

    @BeforeEach
    void setup() {
        client = RestTestClient.bindToApplicationContext(context)
                .apiVersionInserter(ApiVersionInserter.useHeader("API-Version"))
                .build();
    }

    // ==================== BASIC GET REQUESTS ====================

    @Test
    void shouldGetAll{{NAME}}s() {
        List<{{NAME}}VM> items = client.get()
                .uri("/api/{{MODULE}}")
                .exchange()
                .expectStatus().isOk()
                .expectBody(new ParameterizedTypeReference<List<{{NAME}}VM>>() {})
                .returnResult()
                .getResponseBody();

        assertThat(items).isNotNull();
        assertThat(items).hasSizeGreaterThan(0);
    }

    @Test
    void shouldGetById() {
        String id = "TEST-001";

        {{NAME}}VM item = client.get()
                .uri("/api/{{MODULE}}/{id}", id)
                .exchange()
                .expectStatus().isOk()
                .expectBody({{NAME}}VM.class)
                .returnResult()
                .getResponseBody();

        assertThat(item).isNotNull();
        assertThat(item.id()).isEqualTo(id);
    }

    @Test
    void shouldReturn404ForMissingItem() {
        client.get()
                .uri("/api/{{MODULE}}/NONEXISTENT")
                .exchange()
                .expectStatus().isNotFound();
    }

    // ==================== POST REQUESTS ====================

    @Test
    void shouldCreate{{NAME}}() {
        var request = new Create{{NAME}}Request("Test Item", "Description");

        Create{{NAME}}Response response = client.post()
                .uri("/api/{{MODULE}}")
                .bodyValue(request)
                .exchange()
                .expectStatus().isCreated()
                .expectBody(Create{{NAME}}Response.class)
                .returnResult()
                .getResponseBody();

        assertThat(response).isNotNull();
        assertThat(response.id()).isNotNull();
    }

    @Test
    void shouldValidateRequestBody() {
        var invalidRequest = new Create{{NAME}}Request("", "");  // Empty fields

        client.post()
                .uri("/api/{{MODULE}}")
                .bodyValue(invalidRequest)
                .exchange()
                .expectStatus().isBadRequest();
    }

    // ==================== API VERSIONING TESTS ====================

    @Test
    void shouldUseDefaultVersion() {
        List<{{NAME}}VM> items = client.get()
                .uri("/api/{{MODULE}}/search?q=test")
                .exchange()
                .expectStatus().isOk()
                .expectBody(new ParameterizedTypeReference<List<{{NAME}}VM>>() {})
                .returnResult()
                .getResponseBody();

        assertThat(items).isNotNull();
    }

    @Test
    void shouldUseVersion1() {
        List<{{NAME}}VM> items = client.get()
                .uri("/api/{{MODULE}}/search?q=test")
                .apiVersion("1.0")  // Sets API-Version header
                .exchange()
                .expectStatus().isOk()
                .expectBody(new ParameterizedTypeReference<List<{{NAME}}VM>>() {})
                .returnResult()
                .getResponseBody();

        assertThat(items).isNotNull();
    }

    @Test
    void shouldUseVersion2() {
        List<{{NAME}}EnrichedVM> items = client.get()
                .uri("/api/{{MODULE}}/search?q=test")
                .apiVersion("2.0")
                .exchange()
                .expectStatus().isOk()
                .expectBody(new ParameterizedTypeReference<List<{{NAME}}EnrichedVM>>() {})
                .returnResult()
                .getResponseBody();

        assertThat(items).isNotNull();
        // V2 returns enriched data with additional fields
        assertThat(items.get(0).details()).isNotNull();
    }

    // ==================== PATCH/DELETE OPERATIONS ====================

    @Test
    void shouldUpdate{{NAME}}() {
        String id = "TEST-001";
        var request = new Update{{NAME}}Request("Updated Name");

        client.patch()
                .uri("/api/{{MODULE}}/{id}", id)
                .bodyValue(request)
                .exchange()
                .expectStatus().isOk();

        // Verify update
        {{NAME}}VM updated = client.get()
                .uri("/api/{{MODULE}}/{id}", id)
                .exchange()
                .expectBody({{NAME}}VM.class)
                .returnResult()
                .getResponseBody();

        assertThat(updated.name()).isEqualTo("Updated Name");
    }

    @Test
    void shouldDelete{{NAME}}() {
        String id = "TEST-DELETE";

        client.delete()
                .uri("/api/{{MODULE}}/{id}", id)
                .exchange()
                .expectStatus().isNoContent();

        // Verify deletion
        client.get()
                .uri("/api/{{MODULE}}/{id}", id)
                .exchange()
                .expectStatus().isNotFound();
    }

    // ==================== QUERY PARAMETERS ====================

    @Test
    void shouldSearchWithQueryParams() {
        List<{{NAME}}VM> items = client.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/{{MODULE}}/search")
                        .queryParam("q", "test")
                        .queryParam("status", "ACTIVE")
                        .build())
                .exchange()
                .expectStatus().isOk()
                .expectBody(new ParameterizedTypeReference<List<{{NAME}}VM>>() {})
                .returnResult()
                .getResponseBody();

        assertThat(items).allMatch(item -> item.status().equals("ACTIVE"));
    }

    // ==================== CUSTOM HEADERS ====================

    @Test
    void shouldSendCustomHeaders() {
        client.get()
                .uri("/api/{{MODULE}}")
                .header("X-Request-ID", "test-123")
                .header("X-Client-Version", "1.0")
                .exchange()
                .expectStatus().isOk();
    }

    // ==================== ERROR HANDLING ====================

    @Test
    void shouldHandleServerError() {
        client.get()
                .uri("/api/{{MODULE}}/error")  // Endpoint that throws exception
                .exchange()
                .expectStatus().is5xxServerError();
    }
}

// ============================================================
// ALTERNATIVE: MockMvcTester (For Unit Tests)
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest;
//
// import org.junit.jupiter.api.Test;
// import org.springframework.beans.factory.annotation.Autowired;
// import org.springframework.boot.test.context.SpringBootTest;
// import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
// import org.springframework.boot.test.mock.mockito.MockBean;
// import org.springframework.test.web.servlet.assertj.MockMvcTester;
// import org.springframework.test.web.servlet.assertj.MvcTestResult;
//
// import java.util.List;
//
// import static org.assertj.core.api.Assertions.assertThat;
// import static org.mockito.Mockito.*;
//
// /**
//  * Unit test using MockMvcTester (Spring Boot 4).
//  *
//  * Use when you want to test controller logic without full integration.
//  * Faster than TestRestClient but doesn't test full HTTP stack.
//  */
// @SpringBootTest
// @AutoConfigureMockMvc
// class {{NAME}}ControllerUnitTest {
//
//     @Autowired
//     MockMvcTester mvc;
//
//     @MockBean
//     {{NAME}}Service service;
//
//     @Test
//     void shouldGetAll() {
//         when(service.findAll()).thenReturn(List.of(
//                 new {{NAME}}VM("1", "Item 1"),
//                 new {{NAME}}VM("2", "Item 2")
//         ));
//
//         MvcTestResult result = mvc.get()
//                 .uri("/api/{{MODULE}}")
//                 .exchange();
//
//         assertThat(result)
//                 .hasStatusOk()
//                 .bodyJson()
//                 .convertTo(List.class)
//                 .satisfies(items -> assertThat(items).hasSize(2));
//
//         verify(service).findAll();
//     }
//
//     @Test
//     void shouldTestApiVersioning() {
//         MvcTestResult result = mvc.get()
//                 .uri("/api/{{MODULE}}/search?q=test")
//                 .apiVersion("2.0")
//                 .exchange();
//
//         assertThat(result).hasStatusOk();
//     }
// }

// ============================================================
// KEY DIFFERENCES: TestRestClient vs TestRestTemplate
// ============================================================

// TestRestTemplate (Old):
// ResponseEntity<{{NAME}}VM> response = restTemplate.getForEntity(
//     "/api/{{MODULE}}/123", {{NAME}}VM.class
// );
// assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
// assertThat(response.getBody().id()).isEqualTo("123");
//
// TestRestClient (New - Spring Boot 4):
// {{NAME}}VM item = client.get()
//     .uri("/api/{{MODULE}}/123")
//     .exchange()
//     .expectStatus().isOk()
//     .expectBody({{NAME}}VM.class)
//     .returnResult()
//     .getResponseBody();
// assertThat(item.id()).isEqualTo("123");
//
// Benefits:
// - More fluent and readable
// - Better type inference
// - Integrated assertions
// - API versioning support built-in
