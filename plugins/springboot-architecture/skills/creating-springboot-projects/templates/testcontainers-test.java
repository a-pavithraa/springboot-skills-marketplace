package {{PACKAGE}};

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Integration test with Testcontainers.
 *
 * Uses real PostgreSQL container for realistic testing.
 */
@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class {{NAME}}IntegrationTest {

    // Option 1: @ServiceConnection (Spring Boot 3.1+, simpler)
    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    // Option 2: @DynamicPropertySource (older approach, more control)
    // @Container
    // static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");
    //
    // @DynamicPropertySource
    // static void configureProperties(DynamicPropertyRegistry registry) {
    //     registry.add("spring.datasource.url", postgres::getJdbcUrl);
    //     registry.add("spring.datasource.username", postgres::getUsername);
    //     registry.add("spring.datasource.password", postgres::getPassword);
    // }

    @Autowired
    TestRestTemplate restTemplate;

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

    // Add more integration tests here
}

// ============================================================
// EXAMPLE: ProductController Integration Test
// ============================================================

// @Testcontainers
// @SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
// class ProductControllerIntegrationTest {
//
//     @Container
//     @ServiceConnection
//     static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");
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
// }

// ============================================================
// EXAMPLE: Repository Test with @DataJpaTest
// ============================================================

// @DataJpaTest
// @Testcontainers
// @AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
// class ProductRepositoryTest {
//
//     @Container
//     @ServiceConnection
//     static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");
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
// }
