package {{PACKAGE}};

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.TestConfiguration;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Integration test with Testcontainers.
 *
 * Uses real PostgreSQL container for realistic testing.
 * Spring Boot 4 pattern with @TestConfiguration and @ServiceConnection.
 *
 * Note: TestRestTemplate is used here for compatibility, but Spring Boot 4
 * recommends RestTestClient for new code (more modern API with fluent interface).
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import({{NAME}}IntegrationTest.TestcontainersConfig.class)
class {{NAME}}IntegrationTest {

    @Autowired
    TestRestTemplate restTemplate;

    // Alternative: Use RestTestClient (Spring Boot 4 recommended approach)
    // @Autowired
    // RestTestClient restClient;

    @Test
    void contextLoads() {
        // Verifies Spring context starts with Testcontainers
    }

    @Test
    void healthEndpointReturnsUp() {
        var response = restTemplate.getForEntity("/actuator/health", String.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).contains("UP");
    }

    // Example using RestTestClient (Spring Boot 4 recommended)
    // @Test
    // void healthEndpointReturnsUpUsingRestClient() {
    //     String health = restClient.get()
    //         .uri("/actuator/health")
    //         .exchange((request, response) -> {
    //             assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    //             return response.bodyTo(String.class);
    //         });
    //     assertThat(health).contains("UP");
    // }

    // Add more integration tests here

    /**
     * Testcontainers configuration for integration tests.
     * Spring Boot 4 pattern: Use @TestConfiguration with @Bean methods.
     */
    @TestConfiguration(proxyBeanMethods = false)
    @Testcontainers
    static class TestcontainersConfig {

        @Container
        static PostgreSQLContainer<?> postgres =
            new PostgreSQLContainer<>(DockerImageName.parse("postgres:18-alpine"));

        @Bean
        @ServiceConnection
        PostgreSQLContainer<?> postgresContainer() {
            return postgres;
        }
    }
}

// ============================================================
// EXAMPLE: ProductController Integration Test
// ============================================================

// @SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
// @Import(ProductControllerIntegrationTest.TestcontainersConfig.class)
// class ProductControllerIntegrationTest {
//
//     @Autowired
//     TestRestTemplate restTemplate;
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
//         var response = restTemplate.postForEntity(
//             "/api/products",
//             request,
//             CreateProductResponse.class
//         );
//
//         assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
//         assertThat(response.getBody().code()).isNotNull();
//     }
//
//     @Test
//     void shouldReturnNotFoundForMissingProduct() {
//         var response = restTemplate.getForEntity(
//             "/api/products/NONEXISTENT",
//             ProblemDetail.class
//         );
//
//         assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
//     }
//
//     @TestConfiguration(proxyBeanMethods = false)
//     @Testcontainers
//     static class TestcontainersConfig {
//         @Container
//         static PostgreSQLContainer<?> postgres =
//             new PostgreSQLContainer<>(DockerImageName.parse("postgres:18-alpine"));
//
//         @Bean
//         @ServiceConnection
//         PostgreSQLContainer<?> postgresContainer() {
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
//         static PostgreSQLContainer<?> postgres =
//             new PostgreSQLContainer<>(DockerImageName.parse("postgres:18-alpine"));
//
//         @Bean
//         @ServiceConnection
//         PostgreSQLContainer<?> postgresContainer() {
//             return postgres;
//         }
//     }
// }
