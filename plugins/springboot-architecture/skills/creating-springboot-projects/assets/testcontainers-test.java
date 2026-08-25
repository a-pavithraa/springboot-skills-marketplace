package {{PACKAGE}};

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Integration test with Testcontainers (Spring Boot 4).
 *
 * Uses a real PostgreSQL container for realistic testing and the Spring
 * Framework 7 RestTestClient for HTTP assertions.
 *
 * Spring Boot 4 requires @AutoConfigureRestTestClient to enable the
 * RestTestClient bean — HTTP test clients are no longer auto-configured
 * by @SpringBootTest alone.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient
@Import({{NAME}}IntegrationTest.TestcontainersConfig.class)
class {{NAME}}IntegrationTest {

    @Autowired
    RestTestClient client;

    @Test
    void contextLoads() {
        // Verifies Spring context starts with Testcontainers
    }

    @Test
    void healthEndpointReturnsUp() {
        client.get()
                .uri("/actuator/health")
                .exchange()
                .expectStatus().isOk()
                .expectBody(String.class)
                .value(body -> assertThat(body).contains("UP"));
    }

    // Add more integration tests here

    /**
     * Testcontainers configuration for integration tests.
     * Spring Boot 4 pattern: Use @TestConfiguration with @Bean methods.
     */
    @TestConfiguration(proxyBeanMethods = false)
    @Testcontainers
    static class TestcontainersConfig {

        @Container
        static PostgreSQLContainer postgres =
            new PostgreSQLContainer(DockerImageName.parse("postgres:18-alpine"));

        @Bean
        @ServiceConnection
        PostgreSQLContainer postgresContainer() {
            return postgres;
        }
    }
}

// ============================================================
// EXAMPLE: ProductController Integration Test
// ============================================================

// @SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
// @AutoConfigureRestTestClient
// @Import(ProductControllerIntegrationTest.TestcontainersConfig.class)
// class ProductControllerIntegrationTest {
//
//     @Autowired
//     RestTestClient client;
//
//     @Autowired
//     ProductRepository productRepository;
//
//     @BeforeEach
//     void setUp() {
//         productRepository.deleteAll();
//     }
//
//     @Test
//     void shouldCreateProduct() {
//         var request = new CreateProductRequest(
//             ProductDetails.of("Test Product", "Description")
//         );
//
//         CreateProductResponse response = client.post()
//                 .uri("/api/products")
//                 .bodyValue(request)
//                 .exchange()
//                 .expectStatus().isCreated()
//                 .expectBody(CreateProductResponse.class)
//                 .returnResult()
//                 .getResponseBody();
//
//         assertThat(response.code()).isNotNull();
//     }
//
//     @Test
//     void shouldReturnNotFoundForMissingProduct() {
//         client.get()
//                 .uri("/api/products/NONEXISTENT")
//                 .exchange()
//                 .expectStatus().isNotFound()
//                 .expectBody(ProblemDetail.class);
//     }
//
//     @TestConfiguration(proxyBeanMethods = false)
//     @Testcontainers
//     static class TestcontainersConfig {
//         @Container
//         static PostgreSQLContainer postgres =
//             new PostgreSQLContainer(DockerImageName.parse("postgres:18-alpine"));
//
//         @Bean
//         @ServiceConnection
//         PostgreSQLContainer postgresContainer() {
//             return postgres;
//         }
//     }
// }

// ============================================================
// EXAMPLE: Repository Test with @DataJpaTest
// ============================================================

// @DataJpaTest
// @AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
// @Import(ProductRepositoryTest.TestcontainersConfig.class)
// class ProductRepositoryTest {
//
//     @Autowired
//     ProductRepository repository;
//
//     @Test
//     void shouldFindBySku() {
//         var product = ProductEntity.create(
//             ProductSKU.of("TEST-001"),
//             ProductDetails.of("Test", "Desc"),
//             Price.of(new BigDecimal("10.00")),
//             Quantity.of(100)
//         );
//         repository.save(product);
//
//         var found = repository.findBySku(ProductSKU.of("TEST-001"));
//
//         assertThat(found).isPresent();
//         assertThat(found.get().getSku().code()).isEqualTo("TEST-001");
//     }
//
//     @TestConfiguration(proxyBeanMethods = false)
//     @Testcontainers
//     static class TestcontainersConfig {
//         @Container
//         static PostgreSQLContainer postgres =
//             new PostgreSQLContainer(DockerImageName.parse("postgres:18-alpine"));
//
//         @Bean
//         @ServiceConnection
//         PostgreSQLContainer postgresContainer() {
//             return postgres;
//         }
//     }
// }
